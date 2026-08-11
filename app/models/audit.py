"""
Audit Log models for the Trading Platform
Defines the AuditLog table and related enums for event tracking.
"""
from sqlalchemy import Integer, String, DateTime, Enum, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
import enum
from typing import Optional, Dict, Any
from app.database import Base


class AuditEventType(str, enum.Enum):
    """Categories of audit events"""
    # Authentication
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"

    # User
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"

    # Order
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_EXECUTED = "ORDER_EXECUTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FAILED = "ORDER_FAILED"

    # Limit Order
    LIMIT_ORDER_CREATED = "LIMIT_ORDER_CREATED"
    LIMIT_ORDER_TRIGGERED = "LIMIT_ORDER_TRIGGERED"
    LIMIT_ORDER_EXECUTED = "LIMIT_ORDER_EXECUTED"
    LIMIT_ORDER_CANCELLED = "LIMIT_ORDER_CANCELLED"
    LIMIT_ORDER_EXPIRED = "LIMIT_ORDER_EXPIRED"

    # Stop Loss
    STOP_LOSS_CREATED = "STOP_LOSS_CREATED"
    STOP_LOSS_TRIGGERED = "STOP_LOSS_TRIGGERED"
    STOP_LOSS_EXECUTED = "STOP_LOSS_EXECUTED"
    STOP_LOSS_CANCELLED = "STOP_LOSS_CANCELLED"

    # Wallet
    WALLET_DEBITED = "WALLET_DEBITED"
    WALLET_CREDITED = "WALLET_CREDITED"

    # Position
    POSITION_CREATED = "POSITION_CREATED"
    POSITION_UPDATED = "POSITION_UPDATED"
    POSITION_CLOSED = "POSITION_CLOSED"

    # Market
    STOCK_CREATED = "STOCK_CREATED"
    STOCK_UPDATED = "STOCK_UPDATED"
    STOCK_ACTIVATED = "STOCK_ACTIVATED"
    STOCK_DEACTIVATED = "STOCK_DEACTIVATED"
    TRADING_HALTED = "TRADING_HALTED"
    TRADING_RESUMED = "TRADING_RESUMED"

    # System
    SYSTEM_ERROR = "SYSTEM_ERROR"
    SECURITY_EVENT = "SECURITY_EVENT"


class AuditEntityType(str, enum.Enum):
    """Entities that audit events can relate to"""
    USER = "USER"
    ORDER = "ORDER"
    WALLET = "WALLET"
    POSITION = "POSITION"
    STOCK = "STOCK"
    SYSTEM = "SYSTEM"


class AuditLog(Base):
    """Model for storing immutable system audit events"""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    event_type: Mapped[AuditEventType] = mapped_column(Enum(AuditEventType), nullable=False, index=True)
    entity_type: Mapped[AuditEntityType] = mapped_column(Enum(AuditEntityType), nullable=False, index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    
    # Status (e.g., SUCCESS, FAILED)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # JSON fields for flexible data storage (uses JSON for SQLite compatibility)
    metadata_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    previous_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    new_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # Support IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), index=True)

    __table_args__ = (
        Index('idx_audit_user_event', 'user_id', 'event_type'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, event={self.event_type}, user_id={self.user_id}, entity={self.entity_type}:{self.entity_id})>"
