"""
Student schedule API endpoints.
Enables students to browse classes from courses.csv and view/manage classes in their schedule.
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
    ClassInfoResponse,
    StudentScheduleItem,
    StudentScheduleListResponse,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/student", tags=["student"])


@router.get("/classes", response_model=List[ClassInfoResponse])
def get_available_classes(
    search: Optional[str] = Query(None, description="Search course ID or name"),
    term: Optional[str] = Query(None, description="Filter by term (e.g. Summer 2026, Fall 2026)"),
    modality: Optional[str] = Query(None, description="Filter by modality"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse available classes from current course offerings."""
    query = db.query(CourseRecord)
    
    if search:
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
                    added_at=s.added_at,
                )
            )
            
    return StudentScheduleListResponse(
        student_id=student_id,
        student_name=current_user.full_name,
        student_email=current_user.email,
        total_classes=len(items),
        classes=items,
    )


@router.post("/schedule/add", response_model=StudentScheduleItem, status_code=status.HTTP_201_CREATED)
def add_class_to_schedule(
    req: AddClassRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a course offering section to the student's schedule. Returns complete class information."""
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

    student_id = current_user.student_id or current_user.email.split("@")[0]

    schedule = StudentSchedule(
        user_id=current_user.id,
        student_id=student_id,
        course_record_id=course.id,
        status="Enrolled",
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
