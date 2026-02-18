from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional

import uuid
from datetime import datetime

from backtest.schemas import BacktestRequest, BacktestResponse, BacktestListResponse
from backtest.service import BacktestService


router = APIRouter()
service = BacktestService()


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    백테스트 실행 (동기)
    - 짧은 백테스트용 (< 10초)
    """
    try:
        result = await service.run(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.post("/run/async")
async def run_backtest_async(request: BacktestRequest, background_tasks: BackgroundTasks):
    """
    백테스트 실행 (비동기)
    - 긴 백테스트용 (> 10초)
    - job_id 반환 후 백그라운드 실행
    """
    job_id = str(uuid.uuid4())
    background_tasks.add_task(service.run_and_save, job_id, request)
    return {"job_id": job_id, "status": "submitted"}


@router.get("/status/{job_id}")
async def get_backtest_status(job_id: str):
    """
    백테스트 작업 상태 조회
    """
    status = await service.get_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.get("/result/{job_id}", response_model=BacktestResponse)
async def get_backtest_result(job_id: str):
    """
    백테스트 결과 조회
    """
    result = await service.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@router.get("/history", response_model=BacktestListResponse)
async def get_backtest_history(
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    백테스트 기록 조회 (ClickHouse에서)
    """
    results = await service.get_history(symbol, strategy, limit, offset)
    return results


@router.get("/strategies")
async def list_strategies():
    """
    사용 가능한 전략 목록
    """
    return {
        "strategies": [
            {"name": "ma_cross", "description": "이동평균 크로스"},
            {"name": "rsi_reversal", "description": "RSI 반전"},
            {"name": "support_resistance", "description": "지지/저항"},
            {"name": "momentum", "description": "모멘텀"},
        ]
    }