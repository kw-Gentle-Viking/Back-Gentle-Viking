from pydantic import BaseModel, EmailStr
from datetime import datetime
from pydantic import constr


class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=64)  # 평문은 입력만 받고 저장은 hash로

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
