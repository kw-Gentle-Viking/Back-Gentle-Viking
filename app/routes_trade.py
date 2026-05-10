# app/routes_trade.py
import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db,SessionLocal
from app.dependencies import get_current_user
from app.models import User,TradeLog,Basket
from app.ai_client import AIClient
from app.services_allocation import allocate_portfolio

from pydantic import BaseModel
from app.schemas import AllocationConfig,TickerStrategy
from app.strategy_factory import create_strategy
from backtest.engine.risk import Portfolio

import pandas as pd


router = APIRouter()

# 유저별 자동매매 상태 저장 (메모리)
active_tasks: dict[int, asyncio.Task] = {}
ai_client = AIClient()

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

    try:
        # 1. 초기 데이터 로드 (과거 봉)
        for ticker in tickers:
            # TODO: market-db에서 최근 N개 봉 로드
            # rows = db.query(PriceMin05).filter(...).order_by(asc).limit(50)
            # for row in rows:
            #     strategies[ticker].generate_orders(row, portfolio)  # 워밍업
            print(f"{ticker}: 과거 데이터 워밍업 완료")

        # 2. 실시간 루프
        while True:
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
                    # 새 봉 받아오기
                    # TODO: KIS API 실시간 시세
                    # candle = broker.fetch_price(ticker)
                    # close = float(candle['output']['stck_prpr'])
                    # high = float(candle['output']['stck_hgpr'])
                    # low = float(candle['output']['stck_lwpr'])
                    # volume = int(candle['output']['acml_vol'])
                    close = 50000  # 더미

                    row = pd.Series(
                        {"close": close, "high": close, "low": close, "volume": 0},
                        name=pd.Timestamp.now(),
                    )

                    # AI 추론
                    pred_map = {p["ticker"] : p for p in predictions}
                    signal = pred_map[ticker]["signal"]
                    confidence = pred[ticker]["confidence"]

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
                                # resp = broker.create_order(
                                #     symbol=ticker,
                                #     side=order_signal,
                                #     qty=qty,
                                #     order_type="market",
                                # )
                                # if resp.get("rt_cd") != "0":
                                #     raise Exception(resp.get("msg1"))

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
        print(f"[User {user_id}] 자동매매 중단됨")


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

