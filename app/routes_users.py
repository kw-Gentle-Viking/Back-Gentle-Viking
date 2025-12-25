from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.schemas import UserCreate, UserRead
from app.crud_users import create_user, get_user_by_email, get_user, list_users

router = APIRouter()

@router.post("", response_model=UserRead)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user(db,payload.email,payload.password)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409,detial="이메일 이미 있다")

@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("", response_model=list[UserRead])
def read_users(limit: int = 100, db: Session = Depends(get_db)):
    return list_users(db, limit=limit)