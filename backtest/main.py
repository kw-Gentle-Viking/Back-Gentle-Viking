from fastapi import FastAPI
from backtest.routes import router as backtest_router

app = FastAPI(
    title="Backtest Worker",
    version="0.1.0",
)

app.include_router(backtest_router, prefix="/backtest", tags=["backtest"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "backtest-worker"}
