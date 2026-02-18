import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

MARKET_DB_URL = os.getenv(
    "MARKET_DB_URL",
    "postgresql://trader:traderpass@localhost:5433/market_data"
)

market_engine = create_engine(MARKET_DB_URL, pool_pre_ping=True)
MarketSession = sessionmaker(bind=market_engine, autoflush=False, autocommit=False)
MarketBase = declarative_base()


def get_market_db():
    db = MarketSession()
    try:
        yield db
    finally:
        db.close()


def init_market_schema():
    """raw 스키마 생성"""
    with market_engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.commit()


def ping_market():
    """연결 테스트"""
    with market_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
