from fastapi import APIRouter, Depends

from app.rec_report import get_ai_recommendation
from app.schemas import RecommendationResponse
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import User, RecommendationReport


router = APIRouter()


@router.get("", response_model=RecommendationResponse)
def get_recommend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = get_ai_recommendation(
        db=db,
        user_id=current_user.id,
        persona_id=current_user.risk_score or 3,
    )
    return {
        "report": report,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/history", response_model=list[RecommendationResponse])
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reports = (
        db.query(RecommendationReport)
        .filter(RecommendationReport.user_id == current_user.id)
        .order_by(RecommendationReport.created_at.desc())
        .all()
    )

    return [
        {"report": r.report, "timestamp": r.created_at.isoformat()} for r in reports
    ]
