"""
Pydantic schemas for student class scheduling.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class AddClassRequest(BaseModel):
    course_record_id: int


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
    added_at: datetime


class StudentScheduleListResponse(BaseModel):
    student_id: Optional[str] = None
    student_name: str
    student_email: str
    total_classes: int
    classes: List[StudentScheduleItem]
