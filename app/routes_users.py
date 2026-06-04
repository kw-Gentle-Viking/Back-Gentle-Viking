from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import UserCreate, UserRead, UserProfileUpdate
from app.crud_users import create_user, get_user, list_users, update_user_profile
from app.services_investment import calculate_risk_score

router = APIRouter()


@router.post("", response_model=UserRead, status_code=201)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        risk_score = calculate_risk_score(
            investment_goal=payload.investment_goal,
            investment_period=payload.investment_period,
            risk_tolerance=payload.risk_tolerance,
            investment_experience=payload.investment_experience,
            volatility_preference=payload.volatility_preference,
        )
        return create_user(db, payload, risk_score)
    except IntegrityError as e:
        db.rollback()
        err = str(e.orig).lower()
        if "email" in err:
            raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다")
        elif "username" in err:
            raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다")
        raise HTTPException(status_code=409, detail="중복된 값이 있습니다")


@router.get("/me", response_model=UserRead)
def read_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    investment_field_names = [
        "investment_goal",
        "investment_period",
        "risk_tolerance",
        "investment_experience",
        "volatility_preference",
    ]
    risk_score = None

    if any(name in payload.model_fields_set for name in investment_field_names):
        values = {
            name: getattr(payload, name) if getattr(payload, name) is not None else getattr(current_user, name)
            for name in investment_field_names
        }
        if any(value is None for value in values.values()):
            raise HTTPException(status_code=422, detail="투자성향 항목을 모두 입력해주세요")
        risk_score = calculate_risk_score(**values)

    return update_user_profile(db, current_user, payload, risk_score)


# 개발/디버깅용
@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=list[UserRead])
def read_users(limit: int = 100, db: Session = Depends(get_db)):
    return list_users(db, limit=limit)
