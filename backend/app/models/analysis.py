"""
Analysis run and course analysis result models.
Implements FR-04 (demand analysis), DR-03 (traceability), Module H (analysis history).
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class AnalysisRun(Base):
    """
    Records one execution of the demand analysis engine.
    Preserves method version and dataset reference for traceability (DR-03).
    """
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)  # user-provided label
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    run_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="running")  # running, completed, failed
    method_version = Column(String(50), nullable=False)  # e.g. "1.0.0"
    parameters_json = Column(Text, nullable=True)  # JSON of thresholds used
    error_message = Column(Text, nullable=True)
    courses_analyzed = Column(Integer, default=0)
    is_baseline = Column(Boolean, default=False)  # used as baseline for what-if

    # Relationships
    dataset = relationship("Dataset", back_populates="analysis_runs")
    run_by_user = relationship("User", back_populates="analysis_runs")
    course_analyses = relationship("CourseAnalysis", back_populates="analysis_run", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="analysis_run", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="baseline_analysis", foreign_keys="Scenario.baseline_analysis_id")


class CourseAnalysis(Base):
    """
    Demand analysis results for one course in one analysis run.
    All metrics include explicit limitation flags when data is insufficient.
    """
    __tablename__ = "course_analyses"

    id = Column(Integer, primary_key=True, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False, index=True)
    course_id = Column(String(50), nullable=False, index=True)
    course_name = Column(String(255), nullable=True)

    # Computed metrics (NULL = could not compute, not zero)
    avg_enrollment = Column(Float, nullable=True)
    avg_capacity = Column(Float, nullable=True)
    avg_utilization_pct = Column(Float, nullable=True)   # weighted: sum(enroll)/sum(cap)*100
    peak_enrollment = Column(Integer, nullable=True)
    min_enrollment = Column(Integer, nullable=True)
    total_sections = Column(Integer, default=0)           # valid sections analyzed
    terms_offered = Column(Integer, default=0)            # distinct terms
    terms_list = Column(Text, nullable=True)              # JSON list of terms

    # Full capacity analysis
    full_capacity_count = Column(Integer, nullable=True)  # sections at/near full capacity
    full_capacity_rate = Column(Float, nullable=True)     # proportion 0-1

    # Demand trend
    demand_trend = Column(String(20), nullable=True)      # INCREASING, DECREASING, STABLE, INSUFFICIENT_DATA
    demand_trend_score = Column(Float, nullable=True)     # regression slope (students/term)
    trend_r_squared = Column(Float, nullable=True)        # fit quality

    # Unmet demand
    has_unmet_demand_data = Column(Boolean, default=False)
    avg_unmet_demand = Column(Float, nullable=True)
    total_unmet_demand = Column(Integer, nullable=True)

    # Data quality
    insufficient_data = Column(Boolean, default=False)
    limitations_json = Column(Text, nullable=True)        # JSON list of limitation strings
    evidence_json = Column(Text, nullable=True)           # JSON of supporting observations

    calculated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="course_analyses")
