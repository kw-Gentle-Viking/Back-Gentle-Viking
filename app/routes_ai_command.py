# app/routes_ai_command.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from collections import defaultdict
from datetime import datetime

router = APIRouter()

# 커맨드 큐 (메모리)
command_queue: list[dict] = []


class CommandRequest(BaseModel):
    command: str          # START | STOP | ONCE
    user_id: int
    tickers: list[str] = []
    callback_url: Optional[str] = None


@router.post("/commands/push")
def push_command(payload: CommandRequest):
    """백엔드 내부에서 커맨드 적재 (trade/start 호출 시)"""
    cmd = {
        "command": payload.command,
        "user_id": payload.user_id,
        "tickers": payload.tickers,
        "callback_url": payload.callback_url,
        "created_at": datetime.now().isoformat(),
        "status": "pending",
    }
    command_queue.append(cmd)
    return {"status": "queued", "command": payload.command}


@router.get("/commands/pending")
def get_pending_commands():
    """AI 서버가 polling으로 가져감"""
    pending = [c for c in command_queue if c["status"] == "pending"]

    # 가져간 커맨드는 처리 완료로 표시
    for c in pending:
        c["status"] = "delivered"

    return {"commands": pending}


@router.get("/commands/history")
def get_command_history():
    """커맨드 이력 조회 (디버깅용)"""
    return {"commands": command_queue[-50:]}