

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


class RawPriceDaily(MarketBase):
    """일봉 데이터 (6년치)"""

    __tablename__ = "price_daily"
    __table_args__ = (
        Index("idx_price_daily_ticker_date", "ticker", "trade_date"),
        {"schema": "raw"},
    )

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)

    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)

    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=True)  # 거래대금
    shares_outstanding: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )  # 상장주식수


class RawPriceMin01(MarketBase):
    """1분봉 데이터 (1년치)"""

    __tablename__ = "price_min_01"
    __table_args__ = (
        Index("idx_price_min_01_ticker_datetime", "ticker", "trade_datetime"),
        {"schema": "raw"},
    )

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    trade_datetime: Mapped[datetime] = mapped_column(DateTime, primary_key=True)

    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)

    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=True)  # 거래대금

    bid_size_total: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )  # 매수 총잔량
    ask_size_total: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )  # 매도 총잔량


class RawPriceMin05(MarketBase):
    """5분봉 데이터 (2년치)"""

    __tablename__ = "price_min_05"
    __table_args__ = (
        Index("idx_price_min_05_ticker_datetime", "ticker", "trade_datetime"),
        {"schema": "raw"},
    )

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    trade_datetime: Mapped[datetime] = mapped_column(DateTime, primary_key=True)

    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)

    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=True)

    bid_size_total: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ask_size_total: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class RawPriceMin15(MarketBase):
    """15분봉 데이터 (3년치)"""

    __tablename__ = "price_min_15"
    __table_args__ = (
        Index("idx_price_min_15_ticker_datetime", "ticker", "trade_datetime"),
        {"schema": "raw"},
    )

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    trade_datetime: Mapped[datetime] = mapped_column(DateTime, primary_key=True)

    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)

    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=True)

    bid_size_total: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ask_size_total: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class RawFlowDaily:
    """수급 데이터 (금액 기준)"""

    __tablename__ = "flow_daily"
    __table_args__ = (PrimaryKeyConstraint("ticker", "trade_date"), {"schema": "raw"})

    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    individual_net_amt = Column(BigInteger)  # 개인 순매수 (원)
    foreign_net_amt = Column(BigInteger)  # 외국인 순매수 (원)
    inst_net_amt = Column(BigInteger)  # 기관 순매수 (원)
    market_cap = Column(BigInteger)  # 당일 시가총액 (원)
    created_at = Column(DateTime, default=func.now())


class RawFlowDetailed:
    """기관 내 세부 주체별 순매수 (금액 기준)"""

    __tablename__ = "flow_detailed"
    __table_args__ = (PrimaryKeyConstraint("ticker", "trade_date"), {"schema": "raw"})

    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    fin_inv_net_amt = Column(BigInteger)  # 금융투자 (원)
    trust_net_amt = Column(BigInteger)  # 투신 (원)
    pension_net_amt = Column(BigInteger)  # 연기금 (원)
    private_equity_net_amt = Column(BigInteger)  # 사모펀드 (원)
    bank_net_amt = Column(BigInteger)  # 은행 (원)
    insurance_net_amt = Column(BigInteger)  # 보험 (원)
    etc_finance_net_amt = Column(BigInteger)  # 기타금융 (원)
    etc_corp_net_amt = Column(BigInteger)  # 기타법인 (원)
    etc_foreign_net_amt = Column(BigInteger)  # 기타외국인 (원)
    created_at = Column(DateTime, default=func.now())


class RawMarketDaily:
    """시장/매크로 통합"""

    __tablename__ = "market_daily"
    __table_args__ = {"schema": "raw"}

    trade_date = Column(Date, primary_key=True)
    kospi_close = Column(Float)
    kosdaq_close = Column(Float)
    vkospi = Column(Float)
    program_net_amt = Column(BigInteger)  # 프로그램 매매 (원)
    vix = Column(Float)
    us_10y_yield = Column(Float)
    usd_krw = Column(Float)
    snp500_close = Column(Float)
    nasdaq_close = Column(Float)
    phlx_semi_close = Column(Float)  # 반도체 지수
    created_at = Column(DateTime, default=func.now())


class RawMacroExpansion:
    """매크로 지표"""

    __tablename__ = "macro_expansion"
    __table_args__ = {"schema": "raw"}

    trade_date = Column(Date, primary_key=True)
    wti_crude_oil = Column(Float)  # 유가 (USD/Barrel)
    gold_price = Column(Float)  # 금값 (USD/t oz)
    fed_rate = Column(Float)  # 미 연준 금리 (%)
    kr_base_rate = Column(Float)  # 한국 기준 금리 (%)
    created_at = Column(DateTime, default=func.now())


class RawShortLending:
    """공매도 데이터"""

    __tablename__ = "short_lending"
    __table_args__ = (PrimaryKeyConstraint("ticker", "trade_date"), {"schema": "raw"})

    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    short_vol = Column(BigInteger)  # 당일 공매도 거래량
    short_amt = Column(BigInteger)  # 당일 공매도 거래대금
    lending_balance_amt = Column(BigInteger)  # 대차 잔고 금액 (원)
    created_at = Column(DateTime, default=func.now())


class RawTickerInfo:
    """종목 마스터 (산업군, 섹터 등 정적 정보)"""

    __tablename__ = "ticker_info"
    __table_args__ = {"schema": "raw"}

    ticker = Column(String(10), primary_key=True)
    ticker_name = Column(String(100))
    market_type = Column(String(20))  # KOSPI, KOSDAQ, KONEX
    sector_name = Column(String(100))  # 반도체, 제약, 자동차 등
    listing_date = Column(Date)
    created_at = Column(DateTime, default=func.now())


class RawFinanceQuarterly:
    """분기별 재무 데이터"""

    __tablename__ = "finance_quarterly"
    __table_args__ = (
        PrimaryKeyConstraint("ticker", "account_date", "pub_date"),
        {"schema": "raw"},
    )

    ticker = Column(String(10), nullable=False)
    account_date = Column(String(7), nullable=False)  # 기준년월 (예: '2024-12')
    fs_type = Column(String(10), nullable=False)  # 재무재표 타입 ('연결' or '별도')
    report_type = Column(String(5))  # 보고서 종류 ('1Q', '2Q', '3Q', '4Q')
    pub_date = Column(Date)  # 공시 일자
    revenue = Column(BigInteger)  # 매출액
    operating_profit = Column(BigInteger)  # 영업이익
    net_profit = Column(BigInteger)  # 순이익
    equity = Column(BigInteger)  # 자본총계
    debt = Column(BigInteger)  # 부채총계
    created_at = Column(DateTime, default=func.now())


class RawDailyValuation:
    """기업 가치 지표"""

    __tablename__ = "daily_valuation"
    __table_args__ = (PrimaryKeyConstraint("ticker", "trade_date"), {"schema": "raw"})

    ticker = Column(String(6), nullable=False)
    trade_date = Column(Date, nullable=False)
    eps = Column(Float)
    bps = Column(Float)
    per = Column(Float)
    pbr = Column(Float)
    created_at = Column(DateTime, default=func.now())


class RawStockEvents:
    """주요 공시 및 이벤트 (권리락, 배당락 등)"""

    __tablename__ = "stock_events"
    __table_args__ = (
        PrimaryKeyConstraint("ticker", "event_date", "event_type"),
        {"schema": "raw"},
    )

    ticker = Column(String(10), nullable=False)
    event_date = Column(Date, nullable=False)
    event_type = Column(
        String(50), nullable=False
    )  # 유상증자, 무상증자, 배당락, 액면분할, 실적발표
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())


class RawMarketEvents:
    """시장 이벤트"""

    __tablename__ = "market_events"
    __table_args__ = (
        PrimaryKeyConstraint("event_date", "event_type"),
        {"schema": "raw"},
    )

    event_date = Column(Date, nullable=False)  # 한국 시장 기준 반영일
    event_type = Column(String(20), nullable=False)  # 'FOMC', 'BOK', 'WITCHING_US' 등
    description = Column(String(100))
    original_date = Column(Date)  # 실제 현지 날짜
    created_at = Column(DateTime, default=func.now())


class RawCalendar:
    """캘린더"""

    __tablename__ = "calendar"
    __table_args__ = {"schema": "raw"}

    base_date = Column(Date, primary_key=True)
    day_of_week = Column(Integer)  # 0:일, 1:월 ... 6:토
    is_kr_business_day = Column(Boolean)  # 한국 영업일 여부
    is_us_business_day = Column(Boolean)  # 미국 영업일 여부
    kr_holiday_name = Column(String(50))
    us_holiday_name = Column(String(50))


class RawSectorIndexDaily:
    """KRX 섹터 지수"""

    __tablename__ = "sector_index_daily"
    __table_args__ = (
        PrimaryKeyConstraint("sector_code", "trade_date"),
        {"schema": "raw"},
    )

    sector_code = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(BigInteger)
    trading_value = Column(BigInteger)  # 거래대금 (원)
    change_rate = Column(Float)  # 등락률 (%)
    created_at = Column(DateTime, default=func.now())


class RawSectorInfo:
    """섹터 정보"""

    __tablename__ = "sector_info"
    __table_args__ = {"schema": "raw"}

    sector_code = Column(String(10), primary_key=True)
    sector_name = Column(String(100))
    created_at = Column(DateTime, default=func.now())
