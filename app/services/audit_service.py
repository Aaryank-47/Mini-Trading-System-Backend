"""
Audit Service for the Trading Platform
Handles creation of immutable audit logs and metadata sanitization.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
import json
from typing import Optional, Dict, Any

from app.models.audit import AuditLog, AuditEventType, AuditEntityType

logger = logging.getLogger(__name__)


class AuditService:
    """Service for handling audit logging operations"""

    # Keys to redact from metadata
    SENSITIVE_KEYS = {
        "password", "password_hash", "token", "access_token", 
        "refresh_token", "secret", "secret_key", "api_key",
        "authorization", "credentials"
    }

    @classmethod
    def sanitize_metadata(cls, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Recursively redact sensitive information from metadata dictionaries
        """
        if not data:
            return None
            
        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in cls.SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_metadata(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_metadata(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    @classmethod
    def log(
        cls,
        db: Session,
        event_type: AuditEventType,
        entity_type: AuditEntityType,
        entity_id: Optional[int],
        user_id: Optional[int],
        status: str = "SUCCESS",
        metadata_info: Optional[Dict[str, Any]] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        commit: bool = False
    ) -> Optional[AuditLog]:
        """
        Create a new audit log entry.
        
        Args:
            db: SQLAlchemy session
            event_type: The type of event (AuditEventType enum)
            entity_type: The related entity type (AuditEntityType enum)
            entity_id: ID of the related entity (if applicable)
            user_id: ID of the user who performed the action (if applicable)
            status: SUCCESS or FAILED
            metadata_info: Additional context to store (will be sanitized)
            previous_state: State before the action (will be sanitized)
            new_state: State after the action (will be sanitized)
            ip_address: Source IP address
            user_agent: Client User-Agent string
            request_id: Unique request identifier
            commit: Whether to commit the transaction immediately (default False)
                   If False, it will be committed with the surrounding transaction.
        
        Returns:
            The created AuditLog object, or None if creation failed
        """
        try:
            audit_entry = AuditLog(
                user_id=user_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                status=status,
                metadata_info=cls.sanitize_metadata(metadata_info),
                previous_state=cls.sanitize_metadata(previous_state),
                new_state=cls.sanitize_metadata(new_state),
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id
            )
            
            db.add(audit_entry)
            
            if commit:
                try:
                    db.commit()
                    # Cannot refresh if we just committed outside of main workflow as it might break others?
                    # But if commit=True is passed, caller knows what they are doing.
                except SQLAlchemyError as e:
                    db.rollback()
                    logger.error(f"Database error during audit commit: {e}")
                    return None
            
            # Note: We don't call db.refresh(audit_entry) if we don't commit, 
            # because the ID is generated on commit.
            
            logger.debug(f"Audit log created: {event_type.value} for {entity_type.value}:{entity_id}")
            return audit_entry
            
        except Exception as e:
            # We catch all exceptions to prevent audit logging from breaking main business flows
            logger.error(f"Failed to create audit log: {e}")
            return None
