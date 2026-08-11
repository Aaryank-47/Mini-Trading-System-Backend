import pytest
from app.services.audit_service import AuditService
from app.models.audit import AuditEventType, AuditEntityType, AuditLog

def test_sanitize_metadata_redacts_sensitive_keys():
    metadata = {
        "user": "test_user",
        "password": "my_secret_password",
        "nested": {
            "token": "my_jwt_token",
            "safe_key": "safe_value"
        },
        "list_of_keys": [
            {"secret_key": "some_secret"},
            "plain_string"
        ]
    }
    
    sanitized = AuditService.sanitize_metadata(metadata)
    
    assert sanitized is not None
    assert sanitized["user"] == "test_user"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["safe_key"] == "safe_value"
    assert sanitized["list_of_keys"][0]["secret_key"] == "[REDACTED]"
    assert sanitized["list_of_keys"][1] == "plain_string"

def test_sanitize_metadata_handles_none():
    assert AuditService.sanitize_metadata(None) is None

def test_audit_log_creation(db):
    audit_log = AuditService.log(
        db=db,
        event_type=AuditEventType.USER_CREATED,
        entity_type=AuditEntityType.USER,
        entity_id=1,
        user_id=1,
        status="SUCCESS",
        metadata_info={"email": "test@test.com", "password": "super_secret_password"},
        ip_address="127.0.0.1",
        user_agent="pytest",
        commit=True
    )
    
    assert audit_log is not None
    assert audit_log.id is not None
    assert audit_log.event_type == AuditEventType.USER_CREATED
    assert audit_log.entity_type == AuditEntityType.USER
    assert audit_log.entity_id == 1
    assert audit_log.user_id == 1
    assert audit_log.ip_address == "127.0.0.1"
    
    # Metadata should be sanitized before saving
    assert audit_log.metadata_info["password"] == "[REDACTED]"
    assert audit_log.metadata_info["email"] == "test@test.com"

def test_audit_log_rollback_on_failure(db):
    # This tests the commit=False behavior
    try:
        AuditService.log(
            db=db,
            event_type=AuditEventType.SYSTEM_ERROR,
            entity_type=AuditEntityType.SYSTEM,
            entity_id=None,
            user_id=None,
            status="FAILED",
            commit=False
        )
        db.flush()
        # Simulate an exception in the main transaction
        raise ValueError("Simulated failure")
    except ValueError:
        db.rollback()
        
    # Verify the audit log was not committed due to transaction rollback
    logs = db.query(AuditLog).filter(AuditLog.event_type == AuditEventType.SYSTEM_ERROR).all()
    assert len(logs) == 0
