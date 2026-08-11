"""
Audit Logs API router
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.audit import AuditLog, AuditEventType, AuditEntityType
from app.schemas.audit import AuditLogResponse, PaginatedAuditLogs
from app.security import get_current_user

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
    responses={401: {"description": "Not authorized"}}
)


@router.get("", response_model=PaginatedAuditLogs)
def get_audit_logs(
    event_type: Optional[AuditEventType] = Query(None, description="Filter by event type"),
    entity_type: Optional[AuditEntityType] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated audit logs.
    Normal users can only see their own audit events.
    """
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user_id)

    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    total = query.count()
    
    # Calculate offset
    skip = (page - 1) * size
    
    # Order by newest first
    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(size).all()
    
    pages = (total + size - 1) // size

    return {
        "items": logs,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }
