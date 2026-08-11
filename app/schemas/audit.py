from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.audit import AuditEventType, AuditEntityType

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    event_type: AuditEventType
    entity_type: AuditEntityType
    entity_id: Optional[int]
    status: str
    metadata_info: Optional[Dict[str, Any]] = None
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    created_at: datetime

    class Config: # type: ignore
        orm_mode = True
        from_attributes = True

class PaginatedAuditLogs(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    size: int
    pages: int
