from fastapi import APIRouter
from app.db import ping

router = APIRouter()

@router.get("")
def health():
    return {"ok": True}

@router.get("/db")
def db_health():
    ping()
    return {"db": "ok"}