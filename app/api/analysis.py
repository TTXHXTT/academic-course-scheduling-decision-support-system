"""
Demand analysis API endpoints.
Implements FR-04, Module E.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import AnalysisRun, CourseAnalysis
from app.models.user import User
from app.schemas.analysis import AnalysisRunCreate, AnalysisRunResponse, CourseAnalysisResponse
from app.services.analysis_service import AnalysisService
from app.services.recommendation_service import RecommendationService
from app.services.audit_service import AuditService
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/runs", response_model=AnalysisRunResponse)
def create_analysis_run(
    data: AnalysisRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run demand analysis on a dataset."""
    service = AnalysisService(db)
    run = service.run_analysis(
        dataset_id=data.dataset_id,
        user=current_user,
        name=data.name,
        is_baseline=data.is_baseline,
    )

    # Auto-generate recommendations after analysis
    if run.status == "completed" and run.courses_analyzed > 0:
        rec_service = RecommendationService(db)
        rec_service.generate_recommendations(run.id)

    AuditService(db).log(
        "analysis.run",
        actor=current_user,
        entity_type="AnalysisRun",
        entity_id=run.id,
        detail=f"Analyzed {run.courses_analyzed} courses from dataset {data.dataset_id}"
    )
    return run


@router.get("/runs", response_model=List[AnalysisRunResponse])
def list_analysis_runs(
    dataset_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(AnalysisRun).order_by(AnalysisRun.started_at.desc())
    if dataset_id:
        q = q.filter(AnalysisRun.dataset_id == dataset_id)
    return q.all()


@router.get("/runs/{run_id}", response_model=AnalysisRunResponse)
def get_analysis_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = db.get(AnalysisRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return run


@router.get("/runs/{run_id}/courses", response_model=List[CourseAnalysisResponse])
def get_course_analyses(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(CourseAnalysis).filter(CourseAnalysis.analysis_run_id == run_id).all()


@router.get("/runs/{run_id}/courses/{course_id}", response_model=CourseAnalysisResponse)
def get_course_analysis(
    run_id: int,
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ca = db.query(CourseAnalysis).filter(
        CourseAnalysis.analysis_run_id == run_id,
        CourseAnalysis.course_id == course_id
    ).first()
    if not ca:
        raise HTTPException(status_code=404, detail="Course analysis not found")
    return ca


@router.get("/dashboard")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate dashboard metrics from latest analysis runs."""
    from app.models.dataset import Dataset
    from app.models.recommendation import Recommendation
    from sqlalchemy import func

    total_datasets = db.query(Dataset).count()
    total_runs = db.query(AnalysisRun).count()
    latest_run = db.query(AnalysisRun).filter(AnalysisRun.status == "completed").order_by(AnalysisRun.completed_at.desc()).first()
    total_recommendations = db.query(Recommendation).count()

    if latest_run:
        courses = db.query(CourseAnalysis).filter(CourseAnalysis.analysis_run_id == latest_run.id).all()
        high_util = sum(1 for c in courses if c.avg_utilization_pct and c.avg_utilization_pct >= 85)
        low_util = sum(1 for c in courses if c.avg_utilization_pct and c.avg_utilization_pct < 50)
        increasing = sum(1 for c in courses if c.demand_trend == "INCREASING")
        at_cap = sum(1 for c in courses if c.full_capacity_rate and c.full_capacity_rate >= 0.5)
        high_recs = db.query(Recommendation).filter(
            Recommendation.analysis_run_id == latest_run.id,
            Recommendation.priority == "high"
        ).count()
    else:
        courses = []
        high_util = low_util = increasing = at_cap = high_recs = 0

    return {
        "total_datasets": total_datasets,
        "total_analysis_runs": total_runs,
        "latest_run_id": latest_run.id if latest_run else None,
        "latest_run_at": latest_run.completed_at.isoformat() if latest_run and latest_run.completed_at else None,
        "total_courses_analyzed": latest_run.courses_analyzed if latest_run else 0,
        "total_recommendations": total_recommendations,
        "high_priority_recommendations": high_recs,
        "courses_high_utilization": high_util,
        "courses_low_utilization": low_util,
        "courses_increasing_demand": increasing,
        "courses_at_capacity": at_cap,
    }
