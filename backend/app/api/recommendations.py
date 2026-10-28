"""
Recommendations API.
Implements FR-05, FR-06.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/", response_model=List[RecommendationResponse])
def list_recommendations(
    analysis_run_id: Optional[int] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Recommendation)
    if analysis_run_id:
        q = q.filter(Recommendation.analysis_run_id == analysis_run_id)
    if priority:
        q = q.filter(Recommendation.priority == priority)
    if category:
        q = q.filter(Recommendation.category == category)
    if course_id:
        q = q.filter(Recommendation.course_id.ilike(f"%{course_id}%"))
    recs = q.order_by(Recommendation.created_at.desc()).all()
    for rec in recs:
        rec.evidence  # trigger lazy load
    return recs


@router.get("/{rec_id}", response_model=RecommendationResponse)
def get_recommendation(
    rec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = db.get(Recommendation, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec.evidence  # trigger lazy load
    return rec
