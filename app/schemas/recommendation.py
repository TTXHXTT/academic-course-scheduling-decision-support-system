from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RecommendationEvidenceResponse(BaseModel):
    id: int
    evidence_type: str
    term: Optional[str]
    metric_name: Optional[str]
    metric_value: Optional[float]
    description: str

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    id: int
    analysis_run_id: int
    course_id: str
    course_name: Optional[str]
    category: str
    category_label: str
    priority: str
    title: str
    explanation: str
    rule_applied: str
    rule_description: Optional[str]
    limitations: Optional[str]
    suggested_followup: Optional[str]
    key_metric_name: Optional[str]
    key_metric_value: Optional[float]
    key_metric_threshold: Optional[float]
    insufficient_evidence: bool
    created_at: datetime
    evidence: List[RecommendationEvidenceResponse] = []

    model_config = {"from_attributes": True}
