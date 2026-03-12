from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from pydantic import constr

from enum import IntEnum


class UserCreate(BaseModel):
    name: str
    nickname: str
    email: EmailStr
    phone: str
    password: constr(min_length=8, max_length=64)  # 평문은 입력만 받고 저장은 hash로
    birth_date: date


class InvestmentGoal(IntEnum):
    CAPITAL_PRESERVATION = 1  # 원금 보존
    STABLE_RETURN = 2  # 안정적 수익
    GROWTH = 3  # 수익 추구
    HIGH_RETURN = 4  # 고수익 추구


class InvestmentPeriod(IntEnum):
    UNDER_3M = 1
    THREE_TO_12M = 2
    ONE_TO_3Y = 3
    OVER_3Y = 4


class RiskTolerance(IntEnum):
    VERY_LOW = 1  # -5%만 돼도 불안
    LOW = 2  # -10%까지 가능
    MEDIUM = 3  # -20%까지 가능
    HIGH = 4  # -30% 이상도 가능


class InvestmentExperience(IntEnum):
    NONE = 1  # 경험 없음
    SAVINGS = 2  # 예·적금 위주
    STOCKS = 3  # 주식·ETF
    DERIVATIVES = 4  # 파생/코인 포함


class VolatilityPreference(IntEnum):
    LOW = 1  # 낮은 변동성
    MEDIUM = 2  # 중간
    HIGH = 3  # 높은 변동성


class UserProfileUpdate(BaseModel):
    investment_goal: InvestmentGoal
    investment_period: InvestmentPeriod
    risk_tolerance: RiskTolerance
    investment_experience: InvestmentExperience
    volatility_preference: VolatilityPreference
    risk_score: int


class UserRead(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MarketPriceCreate(BaseModel):
    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str = "KIS"


class MarketPriceRead(MarketPriceCreate):
    class Config:
        from_attributes = True
