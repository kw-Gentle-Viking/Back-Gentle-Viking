from fastapi import APIRouter, Depends

from app.recommend_ai import get_ai_recommendation 
from app.schemas import RecommendationResponse
from datetime import datetime

router = APIRouter()

@router.get("/{persona_id}", response_model=RecommendationResponse)
def get_recommend(persona_id: str):
    return {"report": get_ai_recommendation(persona_id), "timestamp": datetime.now().isoformat()}