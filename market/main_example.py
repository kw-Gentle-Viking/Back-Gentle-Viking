from fastapi import FastAPI

# App DB (유저, 인증)
from app.db import Base, engine
import app.models

# Market DB (시세 데이터)
from market.db_market import market_engine, MarketBase, init_market_schema
import market.raw

# 라우터
from app.routes_auth import router as auth_router
from app.routes_users import router as users_router

# App DB 테이블 생성
Base.metadata.create_all(bind=engine)

# Market DB 스키마 및 테이블 생성
init_market_schema()
MarketBase.metadata.create_all(bind=market_engine)

app = FastAPI(
    title="Trading Platform API",
    version="0.1.0",
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(users_router, prefix="/users", tags=["users"])


@app.get("/")
def root():
    return {"status": "ok", "service": "trading-platform"}


@app.get("/health")
def health():
    return {"status": "healthy"}
