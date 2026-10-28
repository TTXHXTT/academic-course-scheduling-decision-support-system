from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AuditEventResponse(BaseModel):
    id: int
    actor_id: Optional[int]
    actor_email: Optional[str]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    detail: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    status: str

    model_config = {"from_attributes": True}
