from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, func, ForeignKey , UniqueConstraint,Boolean, Index

from datetime import datetime
from app.db import Base

from typing import Optional



class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    provider_sub : Mapped[str | None] = mapped_column(String(128), nullable= True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False,default=False)

    name : Mapped[str | None] = mapped_column(String(128),nullable=True)
    picture: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # token 고유 id (랜덤)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True) 
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # token_hash : refresh token 원문이 아니라 hash
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # 생성 시각 만료 시각 폐기 시각
    created_at: Mapped["datetime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped["datetime"] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional["datetime"]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Rotate 되면서 대체된 다음 token jti
    replaced_by_jti: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # 감사 보안 
    #user_agent: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    #ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
Index("idx_refresh_tokens_user_id", RefreshToken.user_id)
