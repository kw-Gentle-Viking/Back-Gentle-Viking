# app/routes_ai_webhook.py
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import os


from app.services_report import generate_report, save_report
from app.db import SessionLocal
from app.shared_state import realtime_predictions, SIGNAL_MAP, ai_signal_event, warmup_events

from app.schemas import PredictionResult, RealtimePayload, OnceCallbackPayload, WarmupPayload

from app.models import LiveCandle
from app.db import SessionLocal

router = APIRouter()

# AI 서버 인증키
AI_API_KEY = os.getenv("AI_SERVER_API_KEY", "dev-ai-key")

# 유저별 최신 추론 결과 저장 (메모리)
# ticker -> 최신 추론 결과
realtime_predictions: dict[str, dict] = {}

# ONCE 결과 저장 (job_id -> 결과)
once_results: dict[str, dict] = {}

SIGNAL_MAP = {"매수": "BUY", "관망": "HOLD", "매도": "SELL"}



# ── 헬퍼 ──────────────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != AI_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def parse_prediction(result: PredictionResult) -> dict:
    signal = SIGNAL_MAP.get(result.pred_str, "HOLD")
    confidence = max(result.prob_buy, result.prob_hold, result.prob_sell)
    return {
        "ticker": result.ticker,
        "signal": signal,
        "confidence": confidence,
        "prob_buy": result.prob_buy,
        "prob_hold": result.prob_hold,
        "prob_sell": result.prob_sell,
        "trade_datetime": result.trade_datetime,
        "model_version": result.model_version,
    }


# ── 엔드포인트 ──────────────────────────────────────────────────────────────

@router.post("/realtime")
def receive_realtime(
    payload: RealtimePayload,
    x_api_key: str = Header(None),
):
    """5분 자동 추론 결과 수신 (AI 서버 → 백엔드)"""
    verify_api_key(x_api_key)

    for result in payload.results:
        parsed = parse_prediction(result)
        realtime_predictions[result.ticker] = parsed
        print(f" {result.ticker}: {parsed['signal']} "
              f"(B:{result.prob_buy:.3f} H:{result.prob_hold:.3f} S:{result.prob_sell:.3f})")

    return {
        "status": "ok",
        "received": len(payload.results),
    }


@router.post("/callback")
def receive_once_callback(
    payload: OnceCallbackPayload,
    x_api_key: str = Header(None),
):
    """ONCE 추론 결과 수신 (AI 서버 → 백엔드)"""
    verify_api_key(x_api_key)

    parsed_results = []
    for result in payload.results:
        parsed = parse_prediction(result)
        parsed["interpretability"] = result.interpretability
        parsed["pred_str"] = result.pred_str
        parsed["prob_buy"] = result.prob_buy
        parsed["prob_hold"] = result.prob_hold
        parsed["prob_sell"] = result.prob_sell
        parsed["trade_datetime"] = result.trade_datetime
        parsed_results.append(parsed)

    # 보고서 생성 + DB 저장
    db = SessionLocal()
    try:
        for result in parsed_results:
            report = generate_report(result)
            save_report(db, user_id=int(payload.user_id), persona_id=1, report=report)
            print(f"  {result['ticker']} 보고서 생성 완료")
    finally:
        db.close()

    once_results[payload.job_id] = {
        "user_id": payload.user_id,
        "inference_at": payload.inference_at,
        "results": parsed_results,
    }

    return {
        "status": "ok",
        "job_id": payload.job_id,
        "received": len(parsed_results),
    }

@router.get("/predictions/{ticker}")
def get_prediction(ticker: str):
    """특정 종목 최신 추론 결과 조회"""
    pred = realtime_predictions.get(ticker)
    if not pred:
        raise HTTPException(status_code=404, detail="추론 결과 없음")
    return pred


@router.get("/once/{job_id}")
def get_once_result(job_id: str):
    """ONCE 추론 결과 조회"""
    result = once_results.get(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="결과 없음")
    return result


@router.post("/realtime")
def receive_realtime(payload: RealtimePayload, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)

    for result in payload.results:
        parsed = parse_prediction(result)
        realtime_predictions[result.ticker] = parsed

    # trading_loop 깨우기
    ai_signal_event.set()

    return {"status": "ok", "received": len(payload.results)}


@router.post("/warmup")
def receive_warmup(
    payload: WarmupPayload,
    x_api_key: str = Header(None),
):
    verify_api_key(x_api_key)

    db = SessionLocal()
    try:
        for c in payload.candles:
            db.add(LiveCandle(
                ticker=payload.ticker,
                timeframe="5m",
                open=c["open"],
                high=c["high"],
                low=c["low"],
                close=c["close"],
                volume=c["volume"],
                trade_datetime=c["datetime"],
            ))
        db.commit()
    finally:
        db.close()

    for user_id, event in warmup_events.items():
        event.set()

    print(f" {payload.ticker}: 워밍업 {len(payload.candles)}개 수신")
    return {"status": "ok", "received": len(payload.candles)}