from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AnalysisRunCreate(BaseModel):
    dataset_id: int
    name: Optional[str] = None
    is_baseline: bool = False


class AnalysisRunResponse(BaseModel):
    id: int
    name: Optional[str]
    dataset_id: int
    run_by_id: Optional[int]
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    method_version: str
    courses_analyzed: int
    is_baseline: bool
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class CourseAnalysisResponse(BaseModel):
    id: int
    analysis_run_id: int
    course_id: str
    course_name: Optional[str]
    avg_enrollment: Optional[float]
    avg_capacity: Optional[float]
    avg_utilization_pct: Optional[float]
    peak_enrollment: Optional[int]
    min_enrollment: Optional[int]
    total_sections: int
    terms_offered: int
    terms_list: Optional[str]
    full_capacity_count: Optional[int]
    full_capacity_rate: Optional[float]
    demand_trend: Optional[str]
    demand_trend_score: Optional[float]
    trend_r_squared: Optional[float]
    has_unmet_demand_data: bool
    avg_unmet_demand: Optional[float]
    total_unmet_demand: Optional[int]
    insufficient_data: bool
    limitations_json: Optional[str]
    evidence_json: Optional[str]

    model_config = {"from_attributes": True}
