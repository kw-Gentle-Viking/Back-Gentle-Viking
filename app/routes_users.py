from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.schemas import UserCreate, UserRead, UserProfileUpdate
from app.crud_users import (
    create_user,
    get_user_by_email,
    get_user,
    list_users,
    update_user_profile,
)

router = APIRouter()


@router.post("", response_model=UserRead)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="이메일 이미 있다")


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}/profile", response_model=UserRead)
def update_profile(
    user_id: int, payload: UserProfileUpdate, db: Session = Depends(get_db)
):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return update_user_profile(db, user, payload)


@router.get("", response_model=list[UserRead])
def read_users(limit: int = 100, db: Session = Depends(get_db)):
    return list_users(db, limit=limit)
