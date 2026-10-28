"""
User model with role-based access control.
Implements NFR-01 (authentication, authorization).
Roles: department_chair, academic_scheduler, program_coordinator, admin
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    department_chair = "department_chair"
    academic_scheduler = "academic_scheduler"
    program_coordinator = "program_coordinator"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)  # bcrypt hash only, never plaintext
    full_name = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.program_coordinator)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    datasets = relationship("Dataset", back_populates="imported_by_user", foreign_keys="Dataset.imported_by_id")
    analysis_runs = relationship("AnalysisRun", back_populates="run_by_user")
    scenarios = relationship("Scenario", back_populates="created_by_user")
    audit_events = relationship("AuditEvent", back_populates="actor")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"
