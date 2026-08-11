"""
Database models for the Trading Platform
Defines User, Wallet, Order, and Position tables
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, UniqueConstraint, DECIMAL, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
import enum
from typing import Optional, List
from app.database import Base
from decimal import Decimal
from app.models.audit import AuditLog, AuditEventType, AuditEntityType


class User(Base):
    """User model for storing user information"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    wallet: Mapped[Optional["Wallet"]] = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    positions: Mapped[List["Position"]] = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"


class Wallet(Base):
    """Wallet model for tracking user balances"""
    __tablename__ = "wallets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    balance: Mapped[Decimal] = mapped_column(DECIMAL(precision=18, scale=2), default=Decimal('1000000.00'), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wallet")
    
    def __repr__(self):
        return f"<Wallet(user_id={self.user_id}, balance={self.balance})>"


class OrderType(str, enum.Enum):
    """Enum for order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"


class OrderStatus(str, enum.Enum):
    """Enum for order statuses"""
    PENDING = "PENDING"
    TRIGGERED = "TRIGGERED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class OrderSide(str, enum.Enum):
    """Enum for order sides"""
    BUY = "BUY"
    SELL = "SELL"


class Order(Base):
    """Order model for tracking buy/sell orders"""
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), default=OrderType.MARKET, nullable=False, index=True)
    price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(precision=12, scale=2), nullable=True)  # Execution price
    limit_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(precision=12, scale=2), nullable=True)
    stop_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(precision=12, scale=2), nullable=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(precision=18, scale=2), nullable=True)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Composite indexes for Trading Engine
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_status_symbol', 'status', 'symbol'),
        Index('idx_status_symbol_side', 'status', 'symbol', 'side'),
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, symbol={self.symbol}, side={self.side})>"


class Position(Base):
    """Position model for tracking user holdings"""
    __tablename__ = "positions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_price: Mapped[Decimal] = mapped_column(DECIMAL(precision=12, scale=2), default=Decimal('0.00'), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Composite unique constraint on user_id and symbol
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uq_user_symbol'),
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="positions")
    
    def __repr__(self):
        return f"<Position(user_id={self.user_id}, symbol={self.symbol}, qty={self.quantity})>"


class Stock(Base):
    """Stock model for storing master stock/symbol data"""
    __tablename__ = "stocks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    min_price: Mapped[float] = mapped_column(Float, nullable=False)
    max_price: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_active_symbol', 'is_active', 'symbol'),
    )
    
    def __repr__(self):
        return f"<Stock(symbol={self.symbol}, company_name={self.company_name}, is_active={self.is_active})>"
