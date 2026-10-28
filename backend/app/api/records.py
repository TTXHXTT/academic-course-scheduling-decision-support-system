"""
Historical course records query API.
Implements FR-02, FR-03, Module D.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course_record import CourseRecord
from app.models.user import User
from app.schemas.course_record import CourseRecordResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("/", response_model=List[CourseRecordResponse])
def query_records(
    dataset_id: int = Query(...),
    course_id: Optional[str] = None,
    term: Optional[str] = None,
    modality: Optional[str] = None,
    major: Optional[str] = None,
    student_level: Optional[str] = None,
    year: Optional[int] = None,
    exclude_errors: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query and filter historical course records."""
    q = db.query(CourseRecord).filter(CourseRecord.dataset_id == dataset_id)

    if exclude_errors:
        q = q.filter(CourseRecord.excluded_from_analysis == False)
    if course_id:
        q = q.filter(CourseRecord.course_id.ilike(f"%{course_id}%"))
    if term:
        q = q.filter(CourseRecord.term.ilike(f"%{term}%"))
    if modality:
        q = q.filter(CourseRecord.modality.ilike(f"%{modality}%"))
    if major:
        q = q.filter(CourseRecord.major.ilike(f"%{major}%"))
    if student_level:
        q = q.filter(CourseRecord.student_level.ilike(f"%{student_level}%"))
    if year:
        q = q.filter(CourseRecord.year == year)

    offset = (page - 1) * page_size
    return q.offset(offset).limit(page_size).all()


@router.get("/courses", response_model=List[str])
def list_courses(
    dataset_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List distinct course IDs in a dataset."""
    results = (
        db.query(CourseRecord.course_id)
        .filter(CourseRecord.dataset_id == dataset_id)
        .distinct()
        .order_by(CourseRecord.course_id)
        .all()
    )
    return [r[0] for r in results]


@router.get("/terms", response_model=List[str])
def list_terms(
    dataset_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List distinct terms in a dataset."""
    results = (
        db.query(CourseRecord.term)
        .filter(CourseRecord.dataset_id == dataset_id)
        .distinct()
        .all()
    )
    return [r[0] for r in results]


@router.get("/modalities", response_model=List[str])
def list_modalities(
    dataset_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List distinct modalities in a dataset."""
    results = (
        db.query(CourseRecord.modality)
        .filter(CourseRecord.dataset_id == dataset_id, CourseRecord.modality.isnot(None))
        .distinct()
        .all()
    )
    return [r[0] for r in results]


@router.get("/stats")
def dataset_stats(
    dataset_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute summary stats for a dataset."""
    from sqlalchemy import func
    from app.models.dataset import Dataset

    records = db.query(CourseRecord).filter(
        CourseRecord.dataset_id == dataset_id,
        CourseRecord.excluded_from_analysis == False,
    ).all()

    if not records:
        return {"total_records": 0, "message": "No valid records found"}

    total_enrollment = sum(r.enrollment for r in records if r.enrollment is not None)
    total_capacity = sum(r.capacity for r in records if r.capacity is not None and r.capacity > 0)
    courses = len(set(r.course_id for r in records))
    terms = len(set(r.term for r in records))

    at_capacity = sum(
        1 for r in records
        if r.enrollment is not None and r.capacity and r.capacity > 0
        and r.enrollment >= r.capacity * 0.95
    )

    utilization = (total_enrollment / total_capacity * 100) if total_capacity > 0 else None

    return {
        "total_records": len(records),
        "unique_courses": courses,
        "unique_terms": terms,
        "total_enrollment": total_enrollment,
        "total_capacity": total_capacity,
        "aggregate_utilization_pct": round(utilization, 1) if utilization else None,
        "sections_at_capacity": at_capacity,
    }
