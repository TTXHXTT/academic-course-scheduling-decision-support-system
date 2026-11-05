"""
Student schedule API endpoints.
Enables students to browse classes from courses.csv and view/add/modify/drop classes in their schedule.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.user import User
from app.models.course_record import CourseRecord
from app.models.student_schedule import StudentSchedule
from app.schemas.student_schedule import (
    AddClassRequest,
    ModifyScheduleRequest,
    ClassInfoResponse,
    StudentScheduleItem,
    StudentScheduleListResponse,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/student", tags=["student"])


def parse_time_range(time_str: Optional[str]):
    """Parses '10:00-10:50' into (start_mins, end_mins)."""
    if not time_str or "-" not in time_str:
        return None
    try:
        parts = time_str.split("-")
        if len(parts) != 2:
            return None
        def to_mins(s):
            h, m = map(int, s.strip().split(":"))
            return h * 60 + m
        return to_mins(parts[0]), to_mins(parts[1])
    except Exception:
        return None


def find_schedule_conflict(target_course: CourseRecord, existing_schedules: List[StudentSchedule], ignore_schedule_id: Optional[int] = None) -> Optional[dict]:
    """
    Checks if target_course time overlaps with any existing schedule in the same term.
    Returns conflict details dict if conflict found, otherwise None.
    """
    if not target_course.days or not target_course.times:
        return None
    t1 = parse_time_range(target_course.times)
    if not t1:
        return None
    target_days = set(target_course.days.upper())
    
    for s in existing_schedules:
        if ignore_schedule_id and s.id == ignore_schedule_id:
            continue
        c = s.course_record
        if not c or not c.days or not c.times:
            continue
        if c.term != target_course.term:
            continue
        c_days = set(c.days.upper())
        if target_days.intersection(c_days):
            t2 = parse_time_range(c.times)
            if t2:
                # Time overlap condition: start1 < end2 and start2 < end1
                if t1[0] < t2[1] and t2[0] < t1[1]:
                    return {
                        "conflicting_course_id": c.course_id,
                        "conflicting_section": c.section_id or "01",
                        "conflicting_course_name": c.course_name,
                        "days": c.days,
                        "times": c.times,
                        "term": c.term,
                    }
    return None


@router.get("/classes", response_model=List[ClassInfoResponse])
def get_available_classes(
    search: Optional[str] = Query(None, description="Search course ID or name"),
    course_id: Optional[str] = Query(None, description="Exact course ID match"),
    term: Optional[str] = Query(None, description="Filter by term (e.g. Summer 2026, Fall 2026)"),
    modality: Optional[str] = Query(None, description="Filter by modality"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse available classes from current course offerings."""
    query = db.query(CourseRecord)
    
    if course_id:
        query = query.filter(CourseRecord.course_id == course_id.strip())
    elif search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            (CourseRecord.course_id.ilike(search_filter)) |
            (CourseRecord.course_name.ilike(search_filter))
        )
    if term:
        query = query.filter(CourseRecord.term.ilike(f"%{term.strip()}%"))
    if modality:
        query = query.filter(CourseRecord.modality.ilike(f"%{modality.strip()}%"))
        
    records = query.order_by(CourseRecord.course_id, CourseRecord.section_id).offset(offset).limit(limit).all()
    return records


@router.get("/classes/{course_id}/sections", response_model=List[ClassInfoResponse])
def get_course_sections(
    course_id: str,
    term: Optional[str] = Query(None, description="Filter by term"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all available sections for a specific course ID (used for section swapping/modification)."""
    query = db.query(CourseRecord).filter(CourseRecord.course_id == course_id)
    if term:
        query = query.filter(CourseRecord.term.ilike(f"%{term.strip()}%"))
    sections = query.order_by(CourseRecord.section_id).all()
    return sections


@router.get("/schedule", response_model=StudentScheduleListResponse)
def get_my_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all classes in the current student's personal schedule with complete class details."""
    student_id = current_user.student_id or current_user.email.split("@")[0]
    
    schedules = (
        db.query(StudentSchedule)
        .filter(StudentSchedule.user_id == current_user.id)
        .order_by(StudentSchedule.added_at.desc())
        .all()
    )
    
    items = []
    for s in schedules:
        c = s.course_record
        if c:
            items.append(
                StudentScheduleItem(
                    schedule_id=s.id,
                    course_record_id=c.id,
                    course_id=c.course_id,
                    course_name=c.course_name,
                    section_id=c.section_id,
                    term=c.term,
                    days=c.days,
                    times=c.times,
                    modality=c.modality,
                    campus=c.campus,
                    enrollment=c.enrollment,
                    capacity=c.capacity,
                    status=s.status,
                    grade_mode=getattr(s, "grade_mode", "Letter Grade") or "Letter Grade",
                    notes=getattr(s, "notes", None),
                    added_at=s.added_at,
                )
            )
            
    # Assuming standard 3 units per lecture course
    total_units = len(items) * 3

    return StudentScheduleListResponse(
        student_id=student_id,
        student_name=current_user.full_name,
        student_email=current_user.email,
        total_classes=len(items),
        total_units=total_units,
        classes=items,
    )


@router.post("/schedule/add", response_model=StudentScheduleItem, status_code=status.HTTP_201_CREATED)
def add_class_to_schedule(
    req: AddClassRequest,
    allow_conflict: bool = Query(False, description="Allow adding even if a time conflict is detected"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a course offering section to the student's schedule. Validates duplicates and time conflicts."""
    course = db.get(CourseRecord, req.course_record_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class section with ID {req.course_record_id} not found."
        )

    # Check if student already enrolled in this section
    existing = (
        db.query(StudentSchedule)
        .filter(
            StudentSchedule.user_id == current_user.id,
            StudentSchedule.course_record_id == course.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{course.course_id} Section {course.section_id or '01'} is already in your schedule."
        )

    # Check time conflict with other classes in student's schedule
    current_schedules = (
        db.query(StudentSchedule)
        .filter(StudentSchedule.user_id == current_user.id)
        .all()
    )
    conflict = find_schedule_conflict(course, current_schedules)
    if conflict and not allow_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Time conflict detected with {conflict['conflicting_course_id']} ({conflict['days']} {conflict['times']}). Set allow_conflict=true to proceed anyway."
        )

    # Determine whether the class is at or over capacity
    is_full = (
        course.capacity is not None
        and course.enrollment is not None
        and course.enrollment >= course.capacity
    )

    if req.status == "Waitlisted" or is_full:
        enrollment_status = "Waitlisted"
    else:
        enrollment_status = req.status or "Enrolled"

    student_id = current_user.student_id or current_user.email.split("@")[0]

    schedule = StudentSchedule(
        user_id=current_user.id,
        student_id=student_id,
        course_record_id=course.id,
        status=enrollment_status,
        grade_mode=req.grade_mode or "Letter Grade",
        notes=req.notes,
        added_at=datetime.now(timezone.utc),
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return StudentScheduleItem(
        schedule_id=schedule.id,
        course_record_id=course.id,
        course_id=course.course_id,
        course_name=course.course_name,
        section_id=course.section_id,
        term=course.term,
        days=course.days,
        times=course.times,
        modality=course.modality,
        campus=course.campus,
        enrollment=course.enrollment,
        capacity=course.capacity,
        status=schedule.status,
        grade_mode=schedule.grade_mode or "Letter Grade",
        notes=schedule.notes,
        added_at=schedule.added_at,
    )




@router.delete("/schedule/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def drop_class_from_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Drop / remove a class from the student's schedule."""
    schedule = (
        db.query(StudentSchedule)
        .filter(
            StudentSchedule.id == schedule_id,
            StudentSchedule.user_id == current_user.id,
        )
        .first()
    )
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found in your schedule."
        )
        
    db.delete(schedule)
    db.commit()
    return None
