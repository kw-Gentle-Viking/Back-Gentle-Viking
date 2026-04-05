from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from pydantic import constr
from typing import Optional

from enum import IntEnum


class InvestmentGoal(IntEnum):
    CAPITAL_PRESERVATION = 1  # 원금 보존
    STABLE_RETURN = 2  # 안정적 수익
    GROWTH = 3  # 수익 추구
    HIGH_RETURN = 4  # 고수익 추구


class InvestmentPeriod(IntEnum):
    UNDER_3M = 1  # 3개월 미만
    THREE_TO_12M = 2  # 3개월에서 12개월
    ONE_TO_3Y = 3  # 1년에서 3년
    OVER_3Y = 4  # 3년이상


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


class UserCreate(BaseModel):
    name: str
    nickname: str
    email: EmailStr
    phone: str
    password: constr(min_length=8, max_length=64)  # 평문은 입력만 받고 저장은 hash로
    birth_date: date

    investment_goal: InvestmentGoal
    investment_period: InvestmentPeriod
    risk_tolerance: RiskTolerance
    investment_experience: InvestmentExperience
    volatility_preference: VolatilityPreference


class UserProfileUpdate(BaseModel):
    investment_goal: InvestmentGoal
    investment_period: InvestmentPeriod
    risk_tolerance: RiskTolerance
    investment_experience: InvestmentExperience
    volatility_preference: VolatilityPreference


class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str]
    nickname: str
    phone: str
    birth_date: Optional[date]
    picture: Optional[str]
    provider: str
    email_verified: bool

    # 투자성향
    investment_goal: Optional[int]
    investment_period: Optional[int]
    risk_tolerance: Optional[int]
    investment_experience: Optional[int]
    volatility_preference: Optional[int]
    risk_score: Optional[int]

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


class RecommendationResponse(BaseModel):
    report: str
