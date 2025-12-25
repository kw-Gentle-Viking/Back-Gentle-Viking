from fastapi import FastAPI
from app.health import router as health_router
from app.db import Base,engine
import app.models
from app.routes_users import router as users_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hedge-Fund Style Control Plane",
    version="0.1.0",
)

app.include_router(health_router, prefix="/health")
app.include_router(users_router, prefix="/users", tags=["users"])
#app.include_router(prices_router, prefix="/prices", tags=["prices"])


@app.get("/")
def root():
    return {"status": "ok", "service": "control-plane"}