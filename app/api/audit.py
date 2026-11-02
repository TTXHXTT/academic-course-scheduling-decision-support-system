"""
Audit log API.
Implements Module I, AC-15.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditEventResponse
from app.api.deps import get_current_user, can_view_audit

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/", response_model=List[AuditEventResponse])
def list_audit_events(
    action: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(can_view_audit),
):
    """View audit events. Requires admin or department_chair role."""
    q = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc())
    if action:
        q = q.filter(AuditEvent.action.ilike(f"%{action}%"))
    return q.limit(limit).all()
