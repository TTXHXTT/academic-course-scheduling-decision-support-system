from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


VALID_SCENARIO_TYPES = [
    "add_section",
    "change_capacity",
    "change_modality",
    "demand_increase",
    "limit_sections",
]


class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    baseline_analysis_id: int
    scenario_type: str
    parameters: Dict[str, Any]

    @field_validator("scenario_type")
    @classmethod
    def valid_type(cls, v):
        if v not in VALID_SCENARIO_TYPES:
            raise ValueError(f"scenario_type must be one of: {VALID_SCENARIO_TYPES}")
        return v


class ScenarioResultResponse(BaseModel):
    id: int
    course_id: str
    course_name: Optional[str]
    baseline_utilization_pct: Optional[float]
    scenario_utilization_pct: Optional[float]
    baseline_capacity: Optional[int]
    scenario_capacity: Optional[int]
    baseline_sections: Optional[int]
    scenario_sections: Optional[int]
    baseline_demand_trend: Optional[str]
    scenario_demand_trend: Optional[str]
    is_affected: bool
    baseline_value_json: Optional[str]
    scenario_value_json: Optional[str]
    changes_json: Optional[str]
    warnings_json: Optional[str]

    model_config = {"from_attributes": True}


class ScenarioResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    baseline_analysis_id: int
    dataset_id: Optional[int]
    created_by_id: Optional[int]
    created_at: datetime
    scenario_type: str
    parameters_json: str
    status: str
    results: List[ScenarioResultResponse] = []

    model_config = {"from_attributes": True}
