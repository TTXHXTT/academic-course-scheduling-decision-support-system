"""
Audit logging service.
Implements Module I (audit trail), AC-15.
Never logs plaintext passwords or authentication secrets.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.user import User


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        actor: Optional[User] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        detail: Optional[str] = None,
        ip_address: Optional[str] = None,
        status: str = "success",
    ) -> AuditEvent:
        """Create an audit event. Never include passwords or secrets in detail."""
        event = AuditEvent(
            actor_id=actor.id if actor else None,
            actor_email=actor.email if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc),
            status=status,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
