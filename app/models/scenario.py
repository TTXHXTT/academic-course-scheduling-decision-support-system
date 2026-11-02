"""
What-if scenario models.
Implements FR-07, FR-08 (scenario builder and comparison).
Scenarios NEVER modify the original historical data (AC-14).
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class Scenario(Base):
    """
    A what-if scenario comparing a hypothetical change against a baseline analysis.
    The original dataset and baseline results are never modified.
    """
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # References (DR-03 traceability - AC-13)
    baseline_analysis_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Scenario configuration
    scenario_type = Column(String(100), nullable=False)  # add_section, change_capacity, change_modality, demand_increase, limit_sections
    parameters_json = Column(Text, nullable=False)  # JSON of scenario parameters
    status = Column(String(50), default="pending")   # pending, completed, failed

    # Method version for traceability
    method_version = Column(String(50), nullable=True)

    # Relationships
    baseline_analysis = relationship("AnalysisRun", back_populates="scenarios", foreign_keys=[baseline_analysis_id])
    created_by_user = relationship("User", back_populates="scenarios")
    results = relationship("ScenarioResult", back_populates="scenario", cascade="all, delete-orphan")


class ScenarioResult(Base):
    """
    Results for one course in a what-if scenario.
    Preserves both baseline and scenario values for comparison (FR-08).
    """
    __tablename__ = "scenario_results"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False, index=True)
    course_id = Column(String(50), nullable=False)
    course_name = Column(String(255), nullable=True)

    # Comparison values (FR-08)
    baseline_utilization_pct = Column(Float, nullable=True)
    scenario_utilization_pct = Column(Float, nullable=True)
    baseline_capacity = Column(Integer, nullable=True)
    scenario_capacity = Column(Integer, nullable=True)
    baseline_sections = Column(Integer, nullable=True)
    scenario_sections = Column(Integer, nullable=True)
    baseline_demand_trend = Column(String(20), nullable=True)
    scenario_demand_trend = Column(String(20), nullable=True)

    # Full comparison data
    baseline_value_json = Column(Text, nullable=True)   # full baseline metrics
    scenario_value_json = Column(Text, nullable=True)   # full scenario metrics
    changes_json = Column(Text, nullable=True)          # what changed and by how much
    warnings_json = Column(Text, nullable=True)         # any warnings about the scenario
    assumptions_json = Column(Text, nullable=True)      # documented assumptions

    is_affected = Column(Boolean, default=False)  # True if this course was changed by the scenario
    calculated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    scenario = relationship("Scenario", back_populates="results")
