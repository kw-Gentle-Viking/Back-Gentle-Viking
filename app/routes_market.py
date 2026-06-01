# app/routes_market.py
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import text
from app.db import get_market_engine
from app.schemas import OHLCVPayload
import os



router = APIRouter()

AI_API_KEY = os.getenv("AI_SERVER_API_KEY", "dev-ai-key")

TABLE_MAP = {
    "1d": "raw.price_daily",
    "5m": "raw.price_min_05",
    "1m": "raw.price_min_01",
}


def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != AI_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/ohlcv")
def receive_ohlcv(
    payload: OHLCVPayload,
    x_api_key: str = Header(None),
):
    """AI 서버에서 수집한 OHLCV 데이터 수신 → market-db 저장"""
    verify_api_key(x_api_key)

    table = TABLE_MAP.get(payload.timeframe)
    if not table:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 timeframe: {payload.timeframe}")

    engine = get_market_engine()

    # raw 스키마 + 테이블 자동 생성
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        
        if payload.timeframe == "1d":
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    ticker VARCHAR(10),
                    trade_date DATE,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    volume BIGINT,
                    PRIMARY KEY (ticker, trade_date)
                )
            """))
        else:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    ticker VARCHAR(10),
                    trade_datetime TIMESTAMP,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    volume BIGINT,
                    PRIMARY KEY (ticker, trade_datetime)
                )
            """))

    # 데이터 삽입
    inserted = 0
    with engine.begin() as conn:
        for r in payload.records:
            if payload.timeframe == "1d":
                conn.execute(text(f"""
                    INSERT INTO {table} (ticker, trade_date, open, high, low, close, volume)
                    VALUES (:ticker, :dt, :open, :high, :low, :close, :volume)
                    ON CONFLICT (ticker, trade_date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """), {
                    "ticker": r.ticker,
                    "dt": r.trade_datetime,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                })
            else:
                conn.execute(text(f"""
                    INSERT INTO {table} (ticker, trade_datetime, open, high, low, close, volume)
                    VALUES (:ticker, :dt, :open, :high, :low, :close, :volume)
                    ON CONFLICT (ticker, trade_datetime) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """), {
                    "ticker": r.ticker,
                    "dt": r.trade_datetime,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                })
            inserted += 1

    print(f"  {payload.timeframe} 데이터 {inserted}건 저장 완료")
    return {
        "status": "ok",
        "timeframe": payload.timeframe,
        "inserted": inserted,
    }