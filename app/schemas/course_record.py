from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CourseRecordResponse(BaseModel):
    id: int
    course_id: str
    course_name: Optional[str]
    section_id: Optional[str]
    term: str
    year: Optional[int]
    semester: Optional[str]
    days: Optional[str]
    times: Optional[str]
    modality: Optional[str]
    campus: Optional[str]
    enrollment: Optional[int]
    capacity: Optional[int]
    attempted_enrollment: Optional[int]
    unmet_demand: Optional[int]
    student_demand: Optional[int]
    major: Optional[str]
    student_level: Optional[str]
    has_warnings: bool
    excluded_from_analysis: bool

    model_config = {"from_attributes": True}


class CourseRecordFilter(BaseModel):
    course_id: Optional[str] = None
    term: Optional[str] = None
    modality: Optional[str] = None
    major: Optional[str] = None
    student_level: Optional[str] = None
    year: Optional[int] = None
    exclude_errors: bool = True
    page: int = 1
    page_size: int = 50
