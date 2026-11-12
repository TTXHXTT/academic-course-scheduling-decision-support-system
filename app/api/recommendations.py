"""
Recommendations API.
Implements FR-05, FR-06.
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendationStatusUpdate
from app.services.audit_service import AuditService
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("", response_model=List[RecommendationResponse])
@router.get("/", response_model=List[RecommendationResponse])
def list_recommendations(
    analysis_run_id: Optional[int] = None,
    priority: Optional[str] = None,
    confidence_level: Optional[str] = None,
    category: Optional[str] = None,
    recommendation_type: Optional[str] = None,
    action_status: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Recommendation)
    if analysis_run_id:
        q = q.filter(Recommendation.analysis_run_id == analysis_run_id)
    
    # Priority / Confidence filter
    eff_priority = priority or confidence_level
    if eff_priority:
        q = q.filter(Recommendation.priority.ilike(eff_priority))
        
    # Category / Type filter
    eff_cat = category or recommendation_type
    if eff_cat:
        # Match either category slug or label or partial
        cat_search = f"%{eff_cat}%"
        q = q.filter(
            (Recommendation.category.ilike(cat_search)) | 
            (Recommendation.category_label.ilike(cat_search))
        )
        
    # Action / Review status filter
    if action_status:
        q = q.filter(Recommendation.action_status.ilike(action_status))
        
    if course_id:
        q = q.filter(Recommendation.course_id.ilike(f"%{course_id.strip()}%"))
        
    recs = q.order_by(Recommendation.created_at.desc()).limit(limit).all()
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


@router.put("/{rec_id}/status", response_model=RecommendationResponse)
@router.put("/{rec_id}", response_model=RecommendationResponse)
def update_recommendation_status(
    rec_id: int,
    data: RecommendationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record an administrative review / override decision on a recommendation (FR-06).
    Logs the decision and rationale to the audit trail (DR-03, NFR-03).
    """
    rec = db.get(Recommendation, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.action_status = data.action_status.upper()
    rec.decision_notes = data.decision_notes or ""
    rec.reviewed_by_id = current_user.id
    rec.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)

    AuditService(db).log(
        "recommendation.override",
        actor=current_user,
        entity_type="Recommendation",
        entity_id=rec.id,
        detail=f"Status set to {rec.action_status} for {rec.course_id}. Notes: {data.decision_notes or 'None'}"
    )
    rec.evidence  # trigger lazy load
    return rec
