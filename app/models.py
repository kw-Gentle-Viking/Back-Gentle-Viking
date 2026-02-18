from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    func,
    ForeignKey,
    UniqueConstraint,
    Boolean,
    Index,
    Date,
)

from datetime import datetime, date
from app.db import Base

from typing import Optional

from sqlalchemy import Float, BigInteger, PrimaryKeyConstraint, Index


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)

    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    provider_sub: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    nickname: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    picture: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )  # 프로필 사진? 구글에 자동 업로드하면 ?
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # 생년월일

    # 투자성향 설문
    investment_goal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    investment_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    risk_tolerance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    investment_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    volatility_preference: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # token 고유 id (랜덤)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # token_hash : refresh token 원문이 아니라 hash
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # 생성 시각 만료 시각 폐기 시각
    created_at: Mapped["datetime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped["datetime"] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[Optional["datetime"]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Rotate 되면서 대체된 다음 token jti
    replaced_by_jti: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # 감사 보안
    # user_agent: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


Index("idx_refresh_tokens_user_id", RefreshToken.user_id)


class MarketPrice(Base):
    __tablename__ = "market_price"
    __table_args__ = (
        PrimaryKeyConstraint("symbol", "ts", name="pk_market_price"),
        Index("idx_market_price_symbol_ts", "symbol", "ts"),
    )

    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    ts: Mapped["datetime"] = mapped_column(DateTime(timezone=True), nullable=False)

    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="KIS")
