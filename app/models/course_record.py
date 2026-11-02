"""
Course record model - stores historical academic data.
Implements DR-01: all required academic fields.
Field semantics documented to avoid misinterpretation of missing data as zero.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class CourseRecord(Base):
    """
    One row represents one course section offering in one academic term.
    All optional numeric fields use NULL (not 0) for missing data.
    Enrollment > capacity is stored as-is with a validation warning.
    """
    __tablename__ = "course_records"

    id = Column(Integer, primary_key=True, index=True)

    # Source references (DR-03 traceability)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    import_job_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=True)

    # Course identification (DR-01)
    course_id = Column(String(50), nullable=False, index=True)  # e.g. "CS-3500"
    course_name = Column(String(255), nullable=True)
    section_id = Column(String(50), nullable=True)  # e.g. "001", "80"

    # Term information (DR-01)
    term = Column(String(50), nullable=False, index=True)  # e.g. "Fall 2023"
    year = Column(Integer, nullable=True)
    semester = Column(String(20), nullable=True)  # Fall, Spring, Summer, Winter

    # Scheduling information (DR-01)
    days = Column(String(50), nullable=True)   # e.g. "MWF", "TR"
    times = Column(String(100), nullable=True) # e.g. "09:00-10:15"
    modality = Column(String(50), nullable=True, index=True)  # In-Person, Online, Hybrid
    campus = Column(String(100), nullable=True)

    # Enrollment data (DR-01) - NULL means unknown, 0 means actually zero
    enrollment = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=True)
    attempted_enrollment = Column(Integer, nullable=True)  # students who tried to enroll
    unmet_demand = Column(Integer, nullable=True)          # attempted - enrolled
    student_demand = Column(Integer, nullable=True)        # explicit demand field if provided

    # Student information (DR-01)
    major = Column(String(100), nullable=True, index=True)
    student_level = Column(String(50), nullable=True)  # Freshman, Sophomore, Junior, Senior, Graduate

    # Flags
    has_warnings = Column(Boolean, default=False)
    excluded_from_analysis = Column(Boolean, default=False)  # True if record has errors

    # Raw data preservation (DR-03)
    raw_row_json = Column(Text, nullable=True)  # JSON of original CSV row for traceability

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    dataset = relationship("Dataset", back_populates="course_records")
    import_job = relationship("ImportJob", back_populates="course_records")
    recommendation_evidence = relationship("RecommendationEvidence", back_populates="course_record")

    def __repr__(self):
        return f"<CourseRecord id={self.id} course_id={self.course_id} term={self.term}>"
