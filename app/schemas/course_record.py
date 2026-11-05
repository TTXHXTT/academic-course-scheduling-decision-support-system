from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class CourseRecordResponse(BaseModel):
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
    attempted_enrollment: Optional[int] = None
    unmet_demand: Optional[int] = None
    student_demand: Optional[int] = None
    major: Optional[str] = None
    student_level: Optional[str] = None
    has_warnings: bool = False
    excluded_from_analysis: bool = False
    capacity_utilization: Optional[float] = None

    model_config = {"from_attributes": True}


class PaginatedCourseRecords(BaseModel):
    items: List[CourseRecordResponse]
    total: int
    page: int
    page_size: int


class TermTrend(BaseModel):
    term: str
    year: Optional[int] = None
    semester: Optional[str] = None
    sections: int = 0
    enrollment: int = 0
    capacity: int = 0
    capacity_utilization: Optional[float] = None
    unmet_demand: int = 0
    student_demand: int = 0


class CourseTrendSummary(BaseModel):
    course_id: str
    course_name: Optional[str] = None
    terms: List[TermTrend] = []
    total_sections: int = 0
    total_enrollment: int = 0
    total_capacity: int = 0
    overall_utilization_pct: Optional[float] = None
    total_unmet_demand: int = 0
    total_student_demand: int = 0
    trend_direction: str = "INSUFFICIENT_DATA"
    trend_slope: Optional[float] = None


class CourseTrendsResponse(BaseModel):
    dataset_id: int
    courses: Dict[str, CourseTrendSummary]


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
