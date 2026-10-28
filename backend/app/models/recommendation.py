"""
Recommendation and evidence models.
Implements FR-05, FR-06 (recommendations with supporting evidence).
Every recommendation must link to evidence; evidence links to course records (DR-03).
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class Recommendation(Base):
    """
    A single course-offering recommendation with full explanation.
    These are suggestions for human review, not automated decisions.
    """
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False, index=True)
    course_id = Column(String(50), nullable=False, index=True)
    course_name = Column(String(255), nullable=True)

    # Recommendation content (FR-05, FR-06)
    category = Column(String(100), nullable=False)  # e.g. "consider_adding_section"
    category_label = Column(String(200), nullable=False)  # human-readable
    priority = Column(String(20), nullable=False, default="medium")  # high, medium, low, informational
    title = Column(String(500), nullable=False)
    explanation = Column(Text, nullable=False)        # why this recommendation was generated
    rule_applied = Column(String(200), nullable=False) # which rule triggered this
    rule_description = Column(Text, nullable=True)    # description of the rule
    limitations = Column(Text, nullable=True)         # data limitations and uncertainty
    suggested_followup = Column(Text, nullable=True)  # suggested human follow-up action

    # Key metrics that triggered this recommendation
    key_metric_name = Column(String(100), nullable=True)
    key_metric_value = Column(Float, nullable=True)
    key_metric_threshold = Column(Float, nullable=True)

    # Flags
    insufficient_evidence = Column(Boolean, default=False)  # labeled when evidence is weak

    # Source references (DR-03)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    analysis_method_version = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="recommendations")
    evidence = relationship("RecommendationEvidence", back_populates="recommendation", cascade="all, delete-orphan")


class RecommendationEvidence(Base):
    """
    Supporting evidence for a recommendation, linked to specific course records.
    Enables users to inspect why a recommendation was generated (FR-06).
    """
    __tablename__ = "recommendation_evidence"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=False)
    course_record_id = Column(Integer, ForeignKey("course_records.id"), nullable=True)  # specific record if applicable

    evidence_type = Column(String(100), nullable=False)  # e.g. "high_utilization", "full_capacity"
    term = Column(String(50), nullable=True)  # the term this evidence applies to
    metric_name = Column(String(100), nullable=True)  # e.g. "utilization_pct"
    metric_value = Column(Float, nullable=True)
    description = Column(Text, nullable=False)  # human-readable explanation of this evidence item

    # Relationships
    recommendation = relationship("Recommendation", back_populates="evidence")
    course_record = relationship("CourseRecord", back_populates="recommendation_evidence")
