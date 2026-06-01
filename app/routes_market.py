# app/routes_market.py
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Literal
import os
from sqlalchemy import create_engine, text

router = APIRouter()

AI_API_KEY   = os.getenv("AI_SERVER_API_KEY", "dev-ai-key")
MARKET_DB_URL = os.getenv(
    "MARKET_DB_URL", "postgresql://trader:traderpass@localhost:5433/market_data"
)
market_engine = create_engine(MARKET_DB_URL, pool_pre_ping=True)


def verify_key(x_api_key: str):
    if x_api_key != AI_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


class OhlcvRecord(BaseModel):
    ticker: str
    trade_date: str | None = None        # 일봉용
    trade_datetime: str | None = None    # 분봉용
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int


class OhlcvPayload(BaseModel):
    timeframe: Literal["1d", "5m", "1m"]
    records: list[OhlcvRecord]


TABLE_MAP = {
    "1d": ("raw.price_daily",   "trade_date"),
    "5m": ("raw.price_min_05",  "trade_datetime"),
    "1m": ("raw.price_min_01",  "trade_datetime"),
}

INIT_SQLS = {
    "raw.price_daily": """
        CREATE SCHEMA IF NOT EXISTS raw;
        CREATE TABLE IF NOT EXISTS raw.price_daily (
            ticker        VARCHAR(10)      NOT NULL,
            trade_date    DATE             NOT NULL,
            open_price    DOUBLE PRECISION,
            high_price    DOUBLE PRECISION,
            low_price     DOUBLE PRECISION,
            close_price   DOUBLE PRECISION,
            volume        BIGINT,
            PRIMARY KEY (ticker, trade_date)
        );
    """,
    "raw.price_min_05": """
        CREATE SCHEMA IF NOT EXISTS raw;
        CREATE TABLE IF NOT EXISTS raw.price_min_05 (
            ticker          VARCHAR(10)      NOT NULL,
            trade_datetime  TIMESTAMP        NOT NULL,
            open_price      DOUBLE PRECISION,
            high_price      DOUBLE PRECISION,
            low_price       DOUBLE PRECISION,
            close_price     DOUBLE PRECISION,
            volume          BIGINT,
            PRIMARY KEY (ticker, trade_datetime)
        );
    """,
    "raw.price_min_01": """
        CREATE SCHEMA IF NOT EXISTS raw;
        CREATE TABLE IF NOT EXISTS raw.price_min_01 (
            ticker          VARCHAR(10)      NOT NULL,
            trade_datetime  TIMESTAMP        NOT NULL,
            open_price      DOUBLE PRECISION,
            high_price      DOUBLE PRECISION,
            low_price       DOUBLE PRECISION,
            close_price     DOUBLE PRECISION,
            volume          BIGINT,
            PRIMARY KEY (ticker, trade_datetime)
        );
    """,
}


@router.post("/ohlcv")
def receive_ohlcv(payload: OhlcvPayload, x_api_key: str = Header(None)):
    verify_key(x_api_key)

    table, dt_col = TABLE_MAP[payload.timeframe]

    with market_engine.begin() as conn:
        conn.execute(text(INIT_SQLS[table]))

        for r in payload.records:
            dt_val = r.trade_date if payload.timeframe == "1d" else r.trade_datetime
            conn.execute(text(f"""
                INSERT INTO {table} (ticker, {dt_col}, open_price, high_price, low_price, close_price, volume)
                VALUES (:ticker, :dt, :open, :high, :low, :close, :volume)
                ON CONFLICT (ticker, {dt_col}) DO UPDATE SET
                    open_price  = EXCLUDED.open_price,
                    high_price  = EXCLUDED.high_price,
                    low_price   = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume      = EXCLUDED.volume
            """), {
                "ticker": r.ticker, "dt": dt_val,
                "open": r.open_price, "high": r.high_price,
                "low": r.low_price,  "close": r.close_price,
                "volume": r.volume,
            })

    return {"status": "ok", "timeframe": payload.timeframe, "received": len(payload.records)}
