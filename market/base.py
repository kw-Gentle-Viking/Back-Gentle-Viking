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


class BasePriceDaily:
    """정제된 일봉 데이터"""

    __tablename__ = "price_daily"
    __table_args__ = (PrimaryKeyConstraint("ticker", "trade_date"), {"schema": "base"})

    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)  # 수정주가 반영됨
    volume = Column(BigInteger)  # 0 제외됨
    turnover = Column(Float)
    shares_outstanding = Column(BigInteger)


class BasePriceMin05:
    """정제된 5분봉 데이터"""

    __tablename__ = "price_min_05"
    __table_args__ = (
        PrimaryKeyConstraint("ticker", "trade_datetime"),
        {"schema": "base"},
    )

    ticker = Column(String(10), nullable=False)
    trade_datetime = Column(DateTime, nullable=False)  # 09:00~15:30
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(BigInteger)
    turnover = Column(Float)
    bid_size_total = Column(BigInteger)
    ask_size_total = Column(BigInteger)


class BasePriceMin15:
    """정제된 15분봉 데이터"""

    __tablename__ = "price_min_15"
    __table_args__ = (
        PrimaryKeyConstraint("ticker", "trade_datetime"),
        {"schema": "base"},
    )

    ticker = Column(String(10), nullable=False)
    trade_datetime = Column(DateTime, nullable=False)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(BigInteger)
    turnover = Column(Float)
    bid_size_total = Column(BigInteger)
    ask_size_total = Column(BigInteger)


class BaseSectorIndexDaily:
    """정제된 섹터 지수"""

    __tablename__ = "sector_index_daily"
    __table_args__ = (
        PrimaryKeyConstraint("sector_code", "trade_date"),
        {"schema": "base"},
    )

    sector_code = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    sector_name = Column(String(50))
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(BigInteger)
    trading_value = Column(BigInteger)
    change_rate = Column(Float)


class BaseTickerMetadata:
    """종목 메타데이터"""

    __tablename__ = "ticker_metadata"
    __table_args__ = {"schema": "base"}

    ticker = Column(String(10), primary_key=True)
    ticker_name = Column(String(100))
    market_type = Column(String(20))  # KOSPI / KOSDAQ
    listing_date = Column(Date)
    sector_code = Column(String(10))  # 섹터 지수 테이블과 조인 키
    sector_name = Column(String(100))
    sector_id = Column(Integer)  # [학습용] 섹터 임베딩 ID (0 ~ 19)
    market_id = Column(Integer)  # [학습용] 시장 구분 ID (KOSDAQ 0, KOSPI 1)


class BaseStockEvents:
    """정제된 종목 이벤트"""

    __tablename__ = "stock_events"
    __table_args__ = (
        PrimaryKeyConstraint("ticker", "event_date", "event_category"),
        {"schema": "base"},
    )

    ticker = Column(String(10), nullable=False)
    event_date = Column(Date, nullable=False)
    event_category = Column(String(50), nullable=False)  # 표준화된 이벤트명
    event_id = Column(Integer)  # [학습용] 이벤트 종류 임베딩 ID
    description = Column(Text)


class BaseMarketEvents:
    """정제된 시장 이벤트"""

    __tablename__ = "market_events"
    __table_args__ = (
        PrimaryKeyConstraint("event_date", "event_category"),
        {"schema": "base"},
    )

    event_date = Column(Date, nullable=False)
    event_category = Column(String(50), nullable=False)  # FOMC, CPI, 선물옵션만기일 등
    event_id = Column(Integer)  # [학습용] 거시경제 이벤트 종류 임베딩 ID
    description = Column(Text)


class BaseCalendar:
    """정제된 캘린더"""

    __tablename__ = "calendar"
    __table_args__ = {"schema": "base"}

    base_date = Column(Date, primary_key=True)
    day_of_week = Column(Integer)  # 0:일요일 ~ 6:토요일
    is_market_open = Column(Integer)  # 1:개장, 0:휴장
    is_holiday = Column(Integer)  # 1:휴일, 0:평일
    is_short_selling_banned = Column(Integer)  # 공매도 금지 여부


class BaseMarketIndex:
    """시장 지수 (한미 통합)"""

    __tablename__ = "market_index"
    __table_args__ = {"schema": "base"}

    trade_date = Column(Date, primary_key=True)

    # 한국 시장
    kospi_close = Column(Float)
    kosdaq_close = Column(Float)
    vkospi = Column(Float)
    program_net_amt = Column(BigInteger)

    # 미국 시장 (전일 자)
    snp500_close = Column(Float)
    nasdaq_close = Column(Float)
    phlx_semi_close = Column(Float)
    vix = Column(Float)
    us_10y_yield = Column(Float)
    usd_krw = Column(Float)


class BaseMacroEconomic:
    """매크로 경제 지표"""

    __tablename__ = "macro_economic"
    __table_args__ = {"schema": "base"}

    trade_date = Column(Date, primary_key=True)
    wti_crude_oil = Column(Float)
    gold_price = Column(Float)
    fed_rate = Column(Float)
    kr_base_rate = Column(Float)


class BaseInvestorFlow:
    """투자자별 수급"""

    __tablename__ = "investor_flow"
    __table_args__ = (PrimaryKeyConstraint("ticker", "trade_date"), {"schema": "base"})

    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    individual_net_amt = Column(BigInteger)  # 개인 순매수
    foreign_net_amt = Column(BigInteger)  # 외국인 순매수
    inst_net_amt = Column(BigInteger)  # 기관 순매수 (합계)
    fin_inv_net_amt = Column(BigInteger)  # 금융투자
    insurance_net_amt = Column(BigInteger)  # 보험
    trust_net_amt = Column(BigInteger)  # 투신
    pe_net_amt = Column(BigInteger)  # 사모펀드
    bank_net_amt = Column(BigInteger)  # 은행
    pension_net_amt = Column(BigInteger)  # 연기금 ★
    etc_finance_net_amt = Column(BigInteger)  # 기타금융
    nation_gov_net_amt = Column(BigInteger)  # 국가/지자체 ★
    etc_corp_net_amt = Column(BigInteger)  # 기타법인
    etc_foreign_net_amt = Column(BigInteger)  # 기타외국인
    market_cap = Column(BigInteger)  # 시가총액


class BaseShortLending:
    """정제된 공매도 데이터"""

    __tablename__ = "short_lending"
    __table_args__ = (PrimaryKeyConstraint("ticker", "trade_date"), {"schema": "base"})

    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    short_vol = Column(BigInteger)
    short_amt = Column(BigInteger)
    lending_balance_amt = Column(BigInteger)


class BaseDailyValuation:
    """정제된 기업 가치 지표"""

    __tablename__ = "daily_valuation"
    __table_args__ = (PrimaryKeyConstraint("ticker", "trade_date"), {"schema": "base"})

    ticker = Column(String(6), nullable=False)
    trade_date = Column(Date, nullable=False)
    eps = Column(Float)
    bps = Column(Float)
    per = Column(Float)
    pbr = Column(Float)
    created_at = Column(DateTime, default=func.now())
