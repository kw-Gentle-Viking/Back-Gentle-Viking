# app/routes_trade.py
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db,SessionLocal
from app.dependencies import get_current_user
from app.models import User,TradeLog,Basket,LiveCandle
from app.ai_client import AIClient
from app.services_allocation import allocate_portfolio
from app.routes_ai_command import command_queue
from datetime import datetime

from pydantic import BaseModel
from app.schemas import AllocationConfig,TickerStrategy
from app.strategy_factory import create_strategy
from backtest.engine.risk import Portfolio
from typing import Optional

from app.strategy_factory import create_strategy, get_warmup_count, get_timeframe

import pandas as pd
import os
from app.kis_websocket import KISWebSocket


router = APIRouter()

# 유저별 자동매매 상태 저장 (메모리)
active_tasks: dict[int, asyncio.Task] = {}
ai_client = AIClient()

ai_signal_event = asyncio.Event()

warmup_events: dict[int, asyncio.Event] = {}


import mojito

def get_broker():
    """KIS 브로커 인스턴스 생성"""
    try:
        return mojito.KoreaInvestment(
            api_key=os.getenv("KIS_APP_KEY"),
            api_secret=os.getenv("KIS_APP_SECRET"),
            acc_no=os.getenv("KIS_ACC_NO"),
            mock=True,
        )
    except Exception as e:
        print(f" KIS 연결 실패: {e}")
        return None

broker = get_broker()

def get_balance() -> int:
    """KIS API 예수금 조회"""
    if not broker:
        return 10_000_000  # KIS 미연결 시 기본값

    try:
        resp = broker.fetch_balance()
        if resp and "output2" in resp and len(resp["output2"]) > 0:
            data = resp["output2"][0]
            return int(data.get("nrciv_blce", data.get("dnca_tot_amt", 0)))
        return 10_000_000
    except Exception as e:
        print(f"잔고 조회 실패: {e}")
        return 10_000_000

async def trading_loop(user_id: int, tickers: list[str], persona_id: int,
    total_capital: int,
    config: AllocationConfig,
    ticker_strategies: list[TickerStrategy],):
    """유저별 자동매매 루프 (5분 주기)"""
    # strategies = {
    #     t: create_strategy(t, strategy_config.strategy_id, strategy_config.params)
    #     for t in tickers
    # }
    strategies = {}

    # 종목별 다른 전략 생성
    for ts in ticker_strategies:
        strategies[ts.ticker] = create_strategy(
            ts.ticker, ts.strategy_id, ts.params
        )

    # 바구니에 있는데 전략 미지정 종목은 기본 전략
    for t in tickers: 
        if t not in strategies:
            strategies[t] = create_strategy(t,"rsi_revesal",None)
    portfolio = Portfolio()
    portfolio.cash = total_capital
    portfolio.equity = total_capital

    ws = KISWebSocket(
        app_key=os.getenv("KIS_APP_KEY"),
        app_secret=os.getenv("KIS_APP_SECRET"),
    )

    ws_task = asyncio.create_task(ws.connect(tickers))

    try:

        await asyncio.sleep(3) # 구독 완료 대기 


        # ── 1. 워밍업 대기 ──────────────────────────────────────
        print(f"[User {user_id}] 워밍업 데이터 대기 중...")

        warmup_events[user_id] = asyncio.Event()
        try:
            await asyncio.wait_for(warmup_events[user_id].wait(), timeout=60)
            print(f"[User {user_id}] 워밍업 데이터 수신 완료")
        except asyncio.TimeoutError:
            print(f"[User {user_id}] 워밍업 타임아웃")

        # 1. 초기 데이터 로드 (과거 봉)
        for ticker in tickers:
            # TODO: market-db에서 최근 N개 봉 로드
            # rows = db.query(PriceMin05).filter(...).order_by(asc).limit(50)
            # for row in rows:
            #     strategies[ticker].generate_orders(row, portfolio)  # 워밍업
            print(f"{ticker}: 과거 데이터 워밍업 완료")

        db = SessionLocal()
        try:
            for ticker in tickers:
                candles = db.query(LiveCandle)\
                    .filter(LiveCandle.ticker == ticker)\
                    .order_by(LiveCandle.trade_datetime.asc())\
                    .limit(get_warmup_count(
                        next((ts.strategy_id for ts in ticker_strategies if ts.ticker == ticker), "rsi_reversal")
                    )).all()

                for candle in candles:
                    row = pd.Series({
                        "close": candle.close,
                        "high": candle.high,
                        "low": candle.low,
                        "volume": candle.volume,
                    }, name=pd.Timestamp(candle.trade_datetime))
                    strategies[ticker].generate_orders(row, portfolio)

                print(f" {ticker}: {len(candles)}개 봉 워밍업 완료")
        finally:
            db.close()


        # 2. 실시간 루프
        while True:
            try:
                await asyncio.wait_for(ai_signal_event.wait(), timeout=600)
                ai_signal_event.clear()  # 다음 push 대기 위해 리셋
            except asyncio.TimeoutError:
                print(f"  AI push 10분 초과 → 스킵")
                continue
            db = SessionLocal()
            try :
                print(f"[User {user_id}] 자동매매 실행...")

                predictions = [] 
                for ticker in tickers:
                    pred = ai_client.predict(ticker)
                    predictions.append(pred)
                
                allocation = allocate_portfolio(
                predictions=predictions,
                persona_id=persona_id,
                total_capital=total_capital,
                max_weight=config.max_weight,
                cash_reserve=config.cash_reserve,
                min_confidence=config.min_confidence,
                use_persona_boost=config.use_persona_boost,
                )
                allocation_map = {a["ticker"]: a for a in allocation}


                for ticker in tickers:

                    market = ws.get_price(ticker)
                    if not market:
                        print(f" {ticker} : 시세없음 -> 스킵")
                        continue

                    close = market["price"]
                    high = market["high"]
                    low = market["low"]
                    volume = market["volume"]

                    row = pd.Series(
                        {"close": close, "high": high, "low": low, "volume": volume},
                        name=pd.Timestamp.now(),
                    )

                    # AI 추론
                    pred_map = {p["ticker"] : p for p in predictions}
                    signal = pred_map[ticker]["signal"]
                    confidence = pred_map[ticker]["confidence"]

                    if confidence < config.min_confidence:
                        print(f"  {ticker}: 확신도 부족 -> SKIP")
                        continue
                    # if signal == "HOLD":
                    #     print(f"  {ticker}: AI 관망 부족 -> HOLD")
                    #     continue

                    # 전략 필터 (봉 데이터 자동 누적됨)
                    orders = strategies[ticker].generate_orders(row, portfolio)

                    # AI + 전략 일치 시 실행
                    for order in orders:
                        order_signal = "BUY" if order.side.value == "BUY" else "SELL"
                        
                       # 매수: allocation 비중 기반 수량
                        if order_signal == "BUY" and ticker in allocation_map:
                            a = allocation_map[ticker]

                            if signal == order_signal:
                                qty = a["amount"] // close
                            elif signal == "HOLD":
                                qty = (a["amount"] // close) // 2 
                            else:
                                continue

                        # 매도: 보유 수량 기반
                        elif order_signal == "SELL":
                            pos = portfolio.positions.get(ticker)
                            if not pos or pos.qty <= 0:
                                continue

                            if signal == order_signal:
                                qty = pos.qty
                            elif signal == "HOLD":
                                qty = pos.qty // 2
                            else:
                                continue

                        else:
                            continue

                        if qty <= 0:
                            continue
                            
                        # 주문 실행 + 재시도 
                        MAX_RETRY = 3
                        RETRY_DELAY = 10
                        order_status = "FAILED"

                        for attempt in range(MAX_RETRY):
                            try : 
                                #TODO: KIS API 주문
                                resp = broker.create_order(
                                    symbol=ticker,
                                    side=order_signal,
                                    qty=qty,
                                    order_type="market",
                                )
                                if resp.get("rt_cd") != "0":
                                    raise Exception(resp.get("msg1"))

                                order_status = "FILLED"
                                print(f"  {ticker}: {order_signal} 체결 | qty={qty} | {qty*close:,}원")
                                break
                            except Exception as e : 
                                print(f"   {ticker}: 주문 실패 ({attempt+1}/{MAX_RETRY}) - {e}")
                                if attempt < MAX_RETRY - 1:
                                    await asyncio.sleep(RETRY_DELAY)
                                else:
                                    print(f"  {ticker}: 최종 실패")

                        db.add(TradeLog(
                                user_id=user_id,
                                ticker=ticker,
                                side=signal,
                                qty=int(order.qty),
                                price=close,
                                amount=int(order.qty * close),
                                ai_signal=signal,
                                ai_confidence=confidence,
                                strategy_id=strategies[ticker].__class__.__name__,
                                status = order_status, 
                        ))
                        print(f"{ticker}: {order_signal} | qty = {qty} | {qty*close: ,}원")
                            # TODO: KIS API 주문
                        
                db.commit()
            finally :
                db.close()
            await asyncio.sleep(300)  # 5분 대기
    except asyncio.CancelledError:
        await ws.disconnect()
        ws_task.cancel()
        if user_id in warmup_events:
            del warmup_events[user_id]
        print(f" [User {user_id}] 자동매매 중단됨")


async def run_once(
    user_id: int,
    tickers: list[str],
    persona_id: int,
    total_capital: int,
    config: AllocationConfig,
    ticker_strategies: list[TickerStrategy],
):
    """1회 실행"""
    from app.db import SessionLocal

    strategies = {}
    for ts in ticker_strategies:
        strategies[ts.ticker] = create_strategy(ts.ticker, ts.strategy_id, ts.params)
    for t in tickers:
        if t not in strategies:
            strategies[t] = create_strategy(t, "rsi_reversal", None)

    portfolio = Portfolio()
    portfolio.cash = total_capital
    portfolio.equity = total_capital

    db = SessionLocal()
    results = []
    try:
        for ticker in tickers:
            close = 50000  # TODO: KIS API 실시간 시세

            row = pd.Series(
                {"close": close, "high": close, "low": close, "volume": 0},
                name=pd.Timestamp.now(),
            )

            pred = ai_client.predict(ticker)
            signal = pred["signal"]
            confidence = pred["confidence"]

            action = "SKIP"


            if confidence < config.min_confidence:
                action = "SKIP"
            elif signal == "HOLD":
                action = "HOLD"
            else:
                orders = strategies[ticker].generate_orders(row, portfolio)

                for order in orders:
                    order_signal = "BUY" if order.side.value == "BUY" else "SELL"
                    if order_signal == signal:
                        action = signal
                        db.add(TradeLog(
                            user_id=user_id,
                            ticker=ticker,
                            side=signal,
                            qty=int(order.qty),
                            price=close,
                            amount=int(order.qty * close),
                            ai_signal=signal,
                            ai_confidence=confidence,
                            strategy_id=strategies[ticker].__class__.__name__,
                        ))
                    else :
                        action = "HOLD"

            results.append({
                "ticker": ticker,
                "signal": signal,
                "confidence": confidence,
                "action": action,
            })

        db.commit()
    finally:
        db.close()

    return results
    


# routes_trade.py에 추가
class TradeRequest(BaseModel):
    total_capital: Optional[int] = None  # None이면 KIS에서 자동 조회
    ticker_strategies: list[TickerStrategy] = []
    allocation: AllocationConfig = AllocationConfig()


@router.post("/start")
async def start_trading(
    payload: TradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    user_id = current_user.id

    # 총 자본금: 유저가 설정했으면 그거, 아니면 KIS에서 조회
    if payload.total_capital:
        total_capital = payload.total_capital
    else:
        # TODO: KIS API로 예수금 조회
        total_capital = get_balance()
        total_capital = 10_000_000  # 더미

    if user_id in active_tasks and not active_tasks[user_id].done():
        return {"status": "ALREADY_RUNNING", "message": "이미 자동매매 실행 중"}

    items = db.query(Basket).filter(Basket.user_id == user_id).all()
    if not items:
        raise HTTPException(status_code=400, detail="바구니가 비어있습니다")

    tickers = [item.ticker for item in items]

    command_queue.append({
        "command": "START",
        "user_id": current_user.id,
        "tickers": tickers,
        "created_at": datetime.now().isoformat(),
        "status": "pending",
    })



    task = asyncio.create_task(
        trading_loop(
            user_id=user_id,
            tickers=tickers,
            persona_id=current_user.risk_score,
            total_capital=total_capital,
            config=payload.allocation,
            ticker_strategies=payload.ticker_strategies,
        )
    )
    active_tasks[user_id] = task

    return {
        "status": "RUNNING",
        "tickers": tickers,
        "message": "자동매매 시작 (5분 주기)",
    }
    

@router.post("/stop")
async def stop_trading(current_user: User = Depends(get_current_user)):
    user_id = current_user.id

    if user_id in active_tasks and not active_tasks[user_id].done():
        active_tasks[user_id].cancel()
        del active_tasks[user_id]
        return {"status": "STOPPED", "message": "자동매매 중단"}

    command_queue.append({
        "command": "STOP",
        "user_id": current_user.id,
        "tickers": [],
        "created_at": datetime.now().isoformat(),
        "status": "pending",
    })

    return {"status": "NOT_RUNNING", "message": "실행 중인 자동매매 없음"}

@router.post("/once")
async def execute_once(
    payload: TradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = db.query(Basket).filter(Basket.user_id == current_user.id).all()
    if not items:
        raise HTTPException(status_code=400, detail="바구니가 비어있습니다")

    tickers = [item.ticker for item in items]

    results = await run_once(
        user_id=current_user.id,
        tickers=tickers,
        persona_id=current_user.risk_score,
        total_capital=payload.total_capital,
        config=payload.allocation,
        ticker_strategies=payload.ticker_strategies,
    )

    return {
        "status": "ONCE",
        "results": results,
        "message": "1회 실행 완료",
    }


@router.get("/status")
async def get_status(current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    is_running = user_id in active_tasks and not active_tasks[user_id].done()
    return {"status": "RUNNING" if is_running else "STOPPED"}

@router.get("/history")
def get_trade_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = db.query(TradeLog)\
        .filter(TradeLog.user_id == current_user.id)\
        .order_by(TradeLog.created_at.desc())\
        .limit(100).all()

    return [
        {
            "ticker": log.ticker,
            "side": log.side,
            "qty": log.qty,
            "price": log.price,
            "amount": log.amount,
            "ai_signal": log.ai_signal,
            "ai_confidence": log.ai_confidence,
            "strategy_id": log.strategy_id,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]

