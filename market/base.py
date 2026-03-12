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
    Index,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from typing import Optional
from sqlalchemy.sql import func
from market.db_market import MarketBase


class BasePriceDaily(MarketBase):
    __tablename__ = "price_daily"
    __table_args__ = (
        Index("idx_base_price_daily_ticker_date", "ticker", "trade_date"),
        {"schema": "base"},
    )
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    turnover: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shares_outstanding: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class BasePriceMin05(MarketBase):
    __tablename__ = "price_min_05"
    __table_args__ = (
        Index("idx_base_price_min_05_ticker_datetime", "ticker", "trade_datetime"),
        {"schema": "base"},
    )
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    trade_datetime: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    turnover: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_size_total: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ask_size_total: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class BasePriceMin15(MarketBase):
    __tablename__ = "price_min_15"
    __table_args__ = (
        Index("idx_base_price_min_15_ticker_datetime", "ticker", "trade_datetime"),
        {"schema": "base"},
    )
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    trade_datetime: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    turnover: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_size_total: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ask_size_total: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class BaseCalendar(MarketBase):
    __tablename__ = "calendar"
    __table_args__ = {"schema": "base"}
    base_date: Mapped[date] = mapped_column(Date, primary_key=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    is_market_open: Mapped[int] = mapped_column(Integer, nullable=False)
    is_holiday: Mapped[int] = mapped_column(Integer, nullable=False)
    is_short_selling_banned: Mapped[int] = mapped_column(Integer, nullable=False)


class BaseTickerMetadata(MarketBase):
    __tablename__ = "ticker_metadata"
    __table_args__ = {"schema": "base"}
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    ticker_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    market_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    listing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sector_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    sector_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sector_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    market_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class BaseInvestorFlow(MarketBase):
    __tablename__ = "investor_flow"
    __table_args__ = (
        Index("idx_base_investor_flow_ticker_date", "ticker", "trade_date"),
        {"schema": "base"},
    )
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    individual_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    foreign_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    inst_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    fin_inv_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    insurance_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    trust_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    pe_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    bank_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    pension_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    etc_finance_net_amt: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    nation_gov_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    etc_corp_net_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    etc_foreign_net_amt: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    market_cap: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class BaseShortLending(MarketBase):
    __tablename__ = "short_lending"
    __table_args__ = (
        Index("idx_base_short_lending_ticker_date", "ticker", "trade_date"),
        {"schema": "base"},
    )
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    short_vol: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    short_amt: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    lending_balance_amt: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )


class BaseDailyValuation(MarketBase):
    __tablename__ = "daily_valuation"
    __table_args__ = (
        Index("idx_base_daily_valuation_ticker_date", "ticker", "trade_date"),
        {"schema": "base"},
    )
    ticker: Mapped[str] = mapped_column(String(6), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    eps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    per: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pbr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
