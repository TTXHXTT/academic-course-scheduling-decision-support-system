"""
Historical course records query API.
Implements FR-02 (query and filter records), FR-03 (historical trends across available terms), Module D.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.course_record import CourseRecord
from app.models.user import User
from app.schemas.course_record import (
    CourseRecordResponse,
    PaginatedCourseRecords,
    CourseTrendsResponse,
    CourseTrendSummary,
    TermTrend,
)
from app.api.deps import get_current_user
from app.analytics.metrics import compute_demand_trend

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("", response_model=PaginatedCourseRecords)
@router.get("/", response_model=PaginatedCourseRecords)
def query_records(
    dataset_id: int = Query(...),
    course_id: Optional[str] = None,
    search: Optional[str] = None,
    term: Optional[str] = None,
    modality: Optional[str] = None,
    major: Optional[str] = None,
    student_level: Optional[str] = None,
    year: Optional[int] = None,
    min_utilization: Optional[float] = None,
    max_utilization: Optional[float] = None,
    exclude_errors: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FR-02: Query and filter historical academic records by course, term, or modality.
    Supports pagination and text search.
    """
    q = db.query(CourseRecord).filter(CourseRecord.dataset_id == dataset_id)

    if exclude_errors:
        q = q.filter(CourseRecord.excluded_from_analysis == False)

    if search:
        search_pattern = f"%{search}%"
        q = q.filter(
            or_(
                CourseRecord.course_id.ilike(search_pattern),
                CourseRecord.course_name.ilike(search_pattern),
            )
        )
    elif course_id:
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

    # Utilization filters
    if min_utilization is not None:
        q = q.filter(
            CourseRecord.capacity > 0,
            CourseRecord.enrollment.isnot(None),
            (CourseRecord.enrollment * 100.0 / CourseRecord.capacity) >= min_utilization,
        )
    if max_utilization is not None:
        q = q.filter(
            CourseRecord.capacity > 0,
            CourseRecord.enrollment.isnot(None),
            (CourseRecord.enrollment * 100.0 / CourseRecord.capacity) <= max_utilization,
        )

    total = q.count()
    offset = (page - 1) * page_size
    raw_records = q.order_by(CourseRecord.course_id, CourseRecord.term).offset(offset).limit(page_size).all()

    items = []
    for r in raw_records:
        rec_dict = {
            "id": r.id,
            "course_id": r.course_id,
            "course_name": r.course_name,
            "section_id": r.section_id,
            "term": r.term,
            "year": r.year,
            "semester": r.semester,
            "days": r.days,
            "times": r.times,
            "modality": r.modality,
            "campus": r.campus,
            "enrollment": r.enrollment,
            "capacity": r.capacity,
            "attempted_enrollment": r.attempted_enrollment,
            "unmet_demand": r.unmet_demand,
            "student_demand": r.student_demand,
            "major": r.major,
            "student_level": r.student_level,
            "has_warnings": r.has_warnings,
            "excluded_from_analysis": r.excluded_from_analysis,
            "capacity_utilization": (
                round((r.enrollment / r.capacity) * 100.0, 1)
                if (r.enrollment is not None and r.capacity and r.capacity > 0)
                else None
            ),
        }
        items.append(CourseRecordResponse(**rec_dict))

    return PaginatedCourseRecords(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/filter-options")
def get_filter_options(
    dataset_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List distinct filter options for courses, terms, and modalities."""
    terms = [
        r[0]
        for r in db.query(CourseRecord.term)
        .filter(CourseRecord.dataset_id == dataset_id, CourseRecord.term.isnot(None))
        .distinct()
        .order_by(CourseRecord.term)
        .all()
        if r[0]
    ]
    modalities = [
        r[0]
        for r in db.query(CourseRecord.modality)
        .filter(CourseRecord.dataset_id == dataset_id, CourseRecord.modality.isnot(None))
        .distinct()
        .order_by(CourseRecord.modality)
        .all()
        if r[0]
    ]
    courses = [
        r[0]
        for r in db.query(CourseRecord.course_id)
        .filter(CourseRecord.dataset_id == dataset_id, CourseRecord.course_id.isnot(None))
        .distinct()
        .order_by(CourseRecord.course_id)
        .all()
        if r[0]
    ]
    return {
        "terms": terms,
        "modalities": modalities,
        "courses": courses,
    }


@router.get("/trends", response_model=CourseTrendsResponse)
def get_course_trends(
    dataset_id: int = Query(...),
    course_ids: str = Query(..., description="Comma-separated course IDs, e.g. 'CSE-2010,CSE-2020'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FR-03: When a user selects a course or group of courses, the ACS shall provide
    historical enrollment, course capacity utilization and student demand trends across the available terms.
    """
    from app.analytics.metrics import SectionData

    requested_courses = [cid.strip() for cid in course_ids.split(",") if cid.strip()]
    courses_map: Dict[str, CourseTrendSummary] = {}

    for cid in requested_courses:
        records = (
            db.query(CourseRecord)
            .filter(
                CourseRecord.dataset_id == dataset_id,
                CourseRecord.course_id.ilike(cid),
                CourseRecord.excluded_from_analysis == False,
            )
            .all()
        )

        if not records:
            continue

        c_name = next((r.course_name for r in records if r.course_name), cid)

        # Group by term
        terms_data: Dict[str, List[CourseRecord]] = {}
        for r in records:
            terms_data.setdefault(r.term, []).append(r)

        term_trends: List[TermTrend] = []
        tot_enrollment = 0
        tot_capacity = 0
        tot_unmet = 0
        tot_student_demand = 0

        # Sort terms chronologically if year is available
        def term_sort_key(t_name):
            sample = terms_data[t_name][0]
            y = sample.year or 9999
            return (y, t_name)

        sorted_term_names = sorted(terms_data.keys(), key=term_sort_key)

        for t_name in sorted_term_names:
            t_records = terms_data[t_name]
            sections_count = len(t_records)
            term_enrollment = sum(r.enrollment for r in t_records if r.enrollment is not None)
            term_capacity = sum(r.capacity for r in t_records if r.capacity is not None and r.capacity > 0)
            term_unmet = sum(r.unmet_demand for r in t_records if r.unmet_demand is not None)
            term_demand = sum(
                r.student_demand if r.student_demand is not None
                else ((r.enrollment or 0) + (r.unmet_demand or 0))
                for r in t_records
            )

            term_util = (term_enrollment / term_capacity * 100.0) if term_capacity > 0 else None

            tot_enrollment += term_enrollment
            tot_capacity += term_capacity
            tot_unmet += term_unmet
            tot_student_demand += term_demand

            first_rec = t_records[0]
            term_trends.append(
                TermTrend(
                    term=t_name,
                    year=first_rec.year,
                    semester=first_rec.semester,
                    sections=sections_count,
                    enrollment=term_enrollment,
                    capacity=term_capacity,
                    capacity_utilization=round(term_util, 1) if term_util is not None else None,
                    unmet_demand=term_unmet,
                    student_demand=term_demand,
                )
            )

        overall_util = (tot_enrollment / tot_capacity * 100.0) if tot_capacity > 0 else None

        # Compute trend direction using analytics engine function
        sections_data = [
            SectionData(
                course_id=r.course_id,
                term=r.term,
                year=r.year,
                enrollment=r.enrollment,
                capacity=r.capacity,
                unmet_demand=r.unmet_demand,
            )
            for r in records
        ]
        trend_dir, slope, _ = compute_demand_trend(sections_data)

        courses_map[cid] = CourseTrendSummary(
            course_id=cid,
            course_name=c_name,
            terms=term_trends,
            total_sections=len(records),
            total_enrollment=tot_enrollment,
            total_capacity=tot_capacity,
            overall_utilization_pct=round(overall_util, 1) if overall_util is not None else None,
            total_unmet_demand=tot_unmet,
            total_student_demand=tot_student_demand,
            trend_direction=trend_dir,
            trend_slope=round(slope, 2) if slope is not None else None,
        )

    return CourseTrendsResponse(
        dataset_id=dataset_id,
        courses=courses_map,
    )


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

