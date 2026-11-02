"""
Student schedule model - stores courses added to a student's personal schedule.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class StudentSchedule(Base):
    """
    Represents a class section added by a student to their schedule.
    Stores relationship to CourseRecord so full class details are available.
    """
    __tablename__ = "student_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(9), nullable=False, index=True)
    course_record_id = Column(Integer, ForeignKey("course_records.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="Enrolled", nullable=False)
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = relationship("User", back_populates="student_schedules")
    course_record = relationship("CourseRecord")

    def __repr__(self):
        return f"<StudentSchedule student={self.student_id} course_record_id={self.course_record_id}>"
