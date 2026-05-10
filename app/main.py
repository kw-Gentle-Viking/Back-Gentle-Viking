from fastapi import FastAPI
from app.health import router as health_router
from app.db import Base, engine
import app.models

from app.routes_auth import router as auth_router
from app.routes_users import router as users_router
from app.routes_prices import router as prices_router
from backtest.routes import router as backtest_router

from app.routes_rec import router as rec_router

from app.routes_basket import router as basket_router
from app.routes_trade import router as trade_router
# Base.metadata.drop_all(bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Control Plane",
    version="0.1.0",
)

app.include_router(health_router, prefix="/health")
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(prices_router, prefix="/prices", tags=["prices"])
app.include_router(auth_router,prefix="/auth", tags=["auth"])

app.include_router(backtest_router, prefix="/backtest", tags=["backtest"])

app.include_router(rec_router, prefix="/recommendation", tags=["recommendation"])

app.include_router(basket_router, prefix="/basket", tags=["basket"])
app.include_router(trade_router, prefix="/trade", tags=["trade"])


@app.get("/")
def root():
    return {"status": "ok", "service": "control-plane"}
