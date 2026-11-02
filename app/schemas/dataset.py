from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.dataset import DatasetStatus, IssueType, IssueSeverity


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_synthetic: bool = False


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    source_filename: Optional[str]
    imported_at: datetime
    row_count: int
    valid_row_count: int
    status: DatasetStatus
    is_synthetic: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class ValidationIssueResponse(BaseModel):
    id: int
    row_number: Optional[int]
    field_name: Optional[str]
    issue_type: IssueType
    issue_code: str
    message: str
    severity: IssueSeverity
    record_included: bool
    raw_value: Optional[str]

    model_config = {"from_attributes": True}


class ImportJobResponse(BaseModel):
    id: int
    dataset_id: int
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    error_message: Optional[str]
    validation_issues: List[ValidationIssueResponse] = []

    model_config = {"from_attributes": True}
