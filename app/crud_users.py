from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import User
from app.security import hash_password
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from app.schemas import UserCreate


def create_user(db: Session, data: UserCreate):
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        nickname=data.nickname,
        phone=data.phone,
        birth_date=data.birth_date,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(db: Session, user, payload):
    user.investment_goal = payload.investment_goal
    user.investment_period = payload.investment_period
    user.risk_tolerance = payload.risk_tolerance
    user.investment_experience = payload.investment_experience
    user.volatility_preference = payload.volatility_preference
    user.risk_score = payload.risk_score
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    return db.execute(stmt).scalars().first()


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def list_users(db: Session, limit: int = 100) -> list[User]:
    stmt = select(User).order_by(User.id.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())
