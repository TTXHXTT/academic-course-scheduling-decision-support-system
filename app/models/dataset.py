"""
Dataset, ImportJob, and ValidationIssue models.
Implements FR-01 (import), DR-01 (fields), DR-02 (validation), DR-03 (traceability).
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class DatasetStatus(str, enum.Enum):
    pending = "pending"
    importing = "importing"
    valid = "valid"
    partial = "partial"  # imported with warnings
    failed = "failed"


class IssueType(str, enum.Enum):
    missing_required = "missing_required"
    invalid_type = "invalid_type"
    invalid_range = "invalid_range"
    invalid_date = "invalid_date"
    malformed_id = "malformed_id"
    inconsistent_ref = "inconsistent_ref"
    duplicate_record = "duplicate_record"
    enrollment_exceeds_capacity = "enrollment_exceeds_capacity"
    missing_period = "missing_period"
    inconsistent_modality = "inconsistent_modality"
    impossible_value = "impossible_value"
    warning_only = "warning_only"


class IssueSeverity(str, enum.Enum):
    error = "error"      # record excluded from analysis
    warning = "warning"  # record included with caveat


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_filename = Column(String(512), nullable=True)
    imported_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    imported_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    row_count = Column(Integer, default=0)
    valid_row_count = Column(Integer, default=0)
    status = Column(SAEnum(DatasetStatus), default=DatasetStatus.pending)
    is_synthetic = Column(Boolean, default=False)  # Always label synthetic data
    notes = Column(Text, nullable=True)

    # Relationships
    imported_by_user = relationship("User", back_populates="datasets", foreign_keys=[imported_by_id])
    import_jobs = relationship("ImportJob", back_populates="dataset", cascade="all, delete-orphan")
    course_records = relationship("CourseRecord", back_populates="dataset", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="dataset")

    def __repr__(self):
        return f"<Dataset id={self.id} name={self.name} status={self.status}>"


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="running")  # running, completed, failed
    total_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    warning_rows = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Relationships
    dataset = relationship("Dataset", back_populates="import_jobs")
    validation_issues = relationship("ValidationIssue", back_populates="import_job", cascade="all, delete-orphan")
    course_records = relationship("CourseRecord", back_populates="import_job")


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id = Column(Integer, primary_key=True, index=True)
    import_job_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=False)
    row_number = Column(Integer, nullable=True)  # 1-based row in the CSV
    field_name = Column(String(100), nullable=True)
    issue_type = Column(SAEnum(IssueType), nullable=False)
    issue_code = Column(String(50), nullable=False)  # stable code e.g. VAL-001
    message = Column(Text, nullable=False)
    severity = Column(SAEnum(IssueSeverity), nullable=False)
    record_included = Column(Boolean, default=False)  # is record still used in analysis?
    raw_value = Column(Text, nullable=True)  # the problematic raw value

    # Relationships
    import_job = relationship("ImportJob", back_populates="validation_issues")
