"""
Database models for the Trading Platform
Defines User, Wallet, Order, and Position tables
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, UniqueConstraint, DECIMAL, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base
from decimal import Decimal


class User(Base):
    """User model for storing user information"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"


class Wallet(Base):
    """Wallet model for tracking user balances"""
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    balance = Column(DECIMAL(precision=18, scale=2), default=Decimal('1000000.00'), nullable=False)  # ✅ FIXED: Decimal type
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="wallet")
    
    def __repr__(self):
        return f"<Wallet(user_id={self.user_id}, balance={self.balance})>"


class OrderStatus(str, enum.Enum):
    """Enum for order statuses"""
    PENDING = "PENDING"
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
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(precision=12, scale=2), nullable=False)  # ✅ FIXED: Decimal type
    total_amount = Column(DECIMAL(precision=18, scale=2), nullable=False)  # ✅ FIXED: Decimal type
    side = Column(Enum(OrderSide), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.COMPLETED, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # ✅ FIXED: Add composite indexes
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )
    
    # Relationships
    user = relationship("User", back_populates="orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, symbol={self.symbol}, side={self.side})>"


class Position(Base):
    """Position model for tracking user holdings"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    average_price = Column(DECIMAL(precision=12, scale=2), default=Decimal('0.00'), nullable=False)  # ✅ FIXED: Decimal type
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Composite unique constraint on user_id and symbol
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uq_user_symbol'),
    )
    
    # Relationships
    user = relationship("User", back_populates="positions")
    
    def __repr__(self):
        return f"<Position(user_id={self.user_id}, symbol={self.symbol}, qty={self.quantity})>"
