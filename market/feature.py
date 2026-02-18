from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Date,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    create_engine,
)


from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from typing import Optional
from sqlalchemy.sql import func
from market.db_market import MarketBase



class FeatureDailyValuation():
    """기업 가치 피처"""
    __tablename__ = 'daily_valuation'
    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'trade_date'),
        {'schema': 'feature'}
    )
    
    ticker = Column(String(6), nullable=False)
    trade_date = Column(Date, nullable=False)
    
    # 정제된 원본 (Winsorized)
    per = Column(Float)  # 500배 초과→500, 음수→NULL
    pbr = Column(Float)  # 50배 초과→50, 음수→NULL
    
    # 모멘텀 피처
    per_chg_1d = Column(Float)  # PER 전일 대비 변화율
    pbr_chg_1d = Column(Float)  # PBR 전일 대비 변화율
    
    # 추세 피처
    per_ma_60 = Column(Float)   # 60일 이동평균
    
    # 상대가치 피처 (Z-Score)
    per_z_score_250 = Column(Float)  # PER 1년 내 상대적 위치
    pbr_z_score_250 = Column(Float)  # PBR 1년 내 상대적 위치
    
    created_at = Column(DateTime, default=func.now())


class FeatureMarketStatus():
    """시장 상태 피처"""
    __tablename__ = 'market_status'
    __table_args__ = {'schema': 'feature'}
    
    trade_date = Column(Date, primary_key=True)
    
    # 캘린더 정보
    day_of_week = Column(Integer)
    is_holiday = Column(Integer)
    is_short_selling_banned = Column(Integer)
    
    # 거시경제 이벤트
    is_bok = Column(Integer)          # 한국은행 금통위
    is_fomc = Column(Integer)         # 미국 FOMC
    is_witching_kr = Column(Integer)  # 한국 선물옵션 동시만기일
    is_witching_us = Column(Integer)  # 미국 선물옵션 동시만기일


class FeatureStockEventStatus():
    """종목별 이벤트 상태 피처"""
    __tablename__ = 'stock_event_status'
    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'trade_date'),
        {'schema': 'feature'}
    )
    
    ticker = Column(String(6), nullable=False)
    trade_date = Column(Date, nullable=False)
    
    # 자본/주가 변동 이벤트
    is_dividend = Column(Integer)         # 배당
    is_bonus_issue = Column(Integer)      # 무상증자
    is_rights_offering = Column(Integer)  # 유상증자
    is_split = Column(Integer)            # 액면분할
    is_merger = Column(Integer)           # 합병
    
    # 정보성 이벤트
    is_earnings = Column(Integer)         # 실적발표


# =============================================================================
# Database Utility Functions
# =============================================================================

def create_all_tables(engine):
    """모든 테이블 생성"""
    # 스키마 먼저 생성
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS base"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS feature"))
        conn.commit()
    
    # 테이블 생성
    Base.metadata.create_all(engine)
    print("All tables created successfully!")


def get_engine(connection_string: str = None):
    """
    Database engine 생성
    
    Example connection strings:
    - PostgreSQL: "postgresql://user:password@localhost:5432/trading_db"
    - SQLite: "sqlite:///trading.db"
    """
    if connection_string is None:
        connection_string = "postgresql://localhost:5432/trading_db"
    
    return create_engine(connection_string, echo=False)


if __name__ == "__main__":
    # 테스트용
    engine = get_engine("postgresql://user:password@localhost:5432/trading_db")
    create_all_tables(engine)
