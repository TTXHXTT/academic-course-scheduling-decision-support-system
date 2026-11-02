"""
Audit event model.
Implements Module I (audit logging), AC-15 (traceability).
Never stores plaintext passwords or authentication secrets.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditEvent(Base):
    """
    Immutable audit record of significant application actions.
    Actor, action, timestamp, and relevant object IDs are always recorded.
    """
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null for system events
    actor_email = Column(String(255), nullable=True)  # denormalized for readability
    action = Column(String(100), nullable=False, index=True)  # e.g. "user.login", "dataset.import"
    entity_type = Column(String(100), nullable=True)  # e.g. "Dataset", "AnalysisRun"
    entity_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)  # JSON or human-readable detail (no secrets)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    status = Column(String(20), default="success")  # success, failure

    # Relationships
    actor = relationship("User", back_populates="audit_events")

    def __repr__(self):
        return f"<AuditEvent id={self.id} action={self.action} actor={self.actor_email}>"
