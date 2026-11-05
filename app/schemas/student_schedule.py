"""
Pydantic schemas for student class scheduling.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class AddClassRequest(BaseModel):
    course_record_id: int
    grade_mode: Optional[str] = "Letter Grade"
    status: Optional[str] = "Enrolled"
    notes: Optional[str] = None


class ModifyScheduleRequest(BaseModel):
    course_record_id: Optional[int] = None
    grade_mode: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ClassInfoResponse(BaseModel):
    id: int
    course_id: str
    course_name: Optional[str] = None
    section_id: Optional[str] = None
    term: str
    year: Optional[int] = None
    semester: Optional[str] = None
    days: Optional[str] = None
    times: Optional[str] = None
    modality: Optional[str] = None
    campus: Optional[str] = None
    enrollment: Optional[int] = None
    capacity: Optional[int] = None
    major: Optional[str] = None
    student_level: Optional[str] = None

    model_config = {"from_attributes": True}


class StudentScheduleItem(BaseModel):
    schedule_id: int
    course_record_id: int
    course_id: str
    course_name: Optional[str] = None
    section_id: Optional[str] = None
    term: str
    days: Optional[str] = None
    times: Optional[str] = None
    modality: Optional[str] = None
    campus: Optional[str] = None
    enrollment: Optional[int] = None
    capacity: Optional[int] = None
    status: str
    grade_mode: Optional[str] = "Letter Grade"
    notes: Optional[str] = None
    added_at: datetime


class StudentScheduleListResponse(BaseModel):
    student_id: Optional[str] = None
    student_name: str
    student_email: str
    total_classes: int
    total_units: Optional[int] = None
    classes: List[StudentScheduleItem]
