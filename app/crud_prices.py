from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from app.models import MarketPrice
from app.schemas import MarketPriceCreate

def upsert_price(db: Session, item: MarketPriceCreate) -> MarketPrice:
    obj = db.get(MarketPrice, {"symbol": item.symbol, "ts": item.ts})
    if obj is None:
        obj = MarketPrice(**item.model_dump())
        db.add(obj)
    else:
        for k, v in item.model_dump().items():
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def get_prices(db: Session, symbol: str, start: datetime, end: datetime, limit: int = 1000) -> list[MarketPrice]:
    stmt = (
        select(MarketPrice)
        .where(MarketPrice.symbol == symbol)
        .where(MarketPrice.ts >= start)
        .where(MarketPrice.ts <= end)
        .order_by(MarketPrice.ts.asc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())