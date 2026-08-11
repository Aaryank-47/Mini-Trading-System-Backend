import pytest
from app.models.audit import AuditEventType, AuditEntityType, AuditLog

def test_get_audit_logs_unauthorized(client):
    response = client.get("/audit-logs")
    assert response.status_code == 403

def test_get_audit_logs_empty(client, test_user, test_user_headers):
    response = client.get("/audit-logs", headers=test_user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0

def test_get_audit_logs_with_data(client, db, test_user, test_user_headers):
    # Insert dummy audit log
    audit_log = AuditLog(
        user_id=test_user.id,
        event_type=AuditEventType.LOGIN_SUCCESS,
        entity_type=AuditEntityType.USER,
        entity_id=test_user.id,
        status="SUCCESS",
        metadata_info={"browser": "chrome"}
    )
    db.add(audit_log)
    db.commit()

    response = client.get("/audit-logs", headers=test_user_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 1
    assert len(data["items"]) == 1
    
    item = data["items"][0]
    assert item["event_type"] == "LOGIN_SUCCESS"
    assert item["entity_type"] == "USER"
    assert item["metadata_info"]["browser"] == "chrome"

def test_get_audit_logs_filtering(client, db, test_user, test_user_headers):
    # Insert multiple audit logs
    log1 = AuditLog(
        user_id=test_user.id,
        event_type=AuditEventType.LOGIN_SUCCESS,
        entity_type=AuditEntityType.USER,
        entity_id=test_user.id,
        status="SUCCESS"
    )
    log2 = AuditLog(
        user_id=test_user.id,
        event_type=AuditEventType.ORDER_CREATED,
        entity_type=AuditEntityType.ORDER,
        entity_id=999,
        status="SUCCESS"
    )
    db.add_all([log1, log2])
    db.commit()

    # Filter by event type
    response = client.get("/audit-logs?event_type=ORDER_CREATED", headers=test_user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "ORDER_CREATED"

    # Filter by entity type
    response = client.get("/audit-logs?entity_type=USER", headers=test_user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["entity_type"] == "USER"

def test_get_audit_logs_authorization(client, db, test_user, test_user_headers):
    # Insert audit log for a different user
    log_other = AuditLog(
        user_id=test_user.id + 1,
        event_type=AuditEventType.LOGIN_SUCCESS,
        entity_type=AuditEntityType.USER,
        entity_id=test_user.id + 1,
        status="SUCCESS"
    )
    db.add(log_other)
    db.commit()

    # The current user should not see other user's logs
    response = client.get("/audit-logs", headers=test_user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
