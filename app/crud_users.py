from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import User
from app.security import hash_password
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError

def create_user(db: Session, email: str, password: str) -> User:
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    try :
        db.commit()
    except SQLAlchemyError :
        db.rollback()
        raise
    db.refresh(user)
    return user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    return db.execute(stmt).scalars().first()

def get_user(db: Session, user_id: int) ->  Optional[User] :
    return db.get(User, user_id)

def list_users(db: Session, limit: int = 100) -> list[User]:
    stmt = select(User).order_by(User.id.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())