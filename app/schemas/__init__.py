"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ==================== User Schemas ====================
class UserCreate(BaseModel):
    """Schema for creating a new user"""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Wallet Schemas ====================
class WalletResponse(BaseModel):
    """Schema for wallet response"""
    id: int
    user_id: int
    balance: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Order Schemas ====================
class OrderCreate(BaseModel):
    """Schema for creating an order"""
    user_id: int
    symbol: str = Field(..., min_length=1, max_length=50)
    qty: int = Field(..., gt=0)
    side: str = Field(..., pattern="^(BUY|SELL)$")


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: int
    user_id: int
    symbol: str
    quantity: int
    price: float
    total_amount: float
    side: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrderHistoryResponse(BaseModel):
    """Schema for order history"""
    id: int
    symbol: str
    quantity: int
    price: float
    total_amount: float
    side: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Position Schemas ====================
class PositionResponse(BaseModel):
    """Schema for position response"""
    id: int
    user_id: int
    symbol: str
    quantity: int
    average_price: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Portfolio Schemas ====================
class PortfolioItem(BaseModel):
    """Schema for a portfolio holding"""
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    total_invested: float
    current_value: float
    unrealized_pnl: float
    pnl_percentage: float


class PortfolioResponse(BaseModel):
    """Schema for full portfolio response"""
    user_id: int
    wallet_balance: float
    holdings: List[PortfolioItem]
    total_portfolio_value: float
    total_invested: float
    total_unrealized_pnl: float
    total_pnl_percentage: float


# ==================== WebSocket Schemas ====================
class OrderExecutedMessage(BaseModel):
    """Schema for WebSocket order executed message"""
    event: str
    symbol: str
    qty: int
    price: float
    side: str
    status: str
    total_amount: float
    timestamp: datetime


class PriceUpdateMessage(BaseModel):
    """Schema for WebSocket price update message"""
    event: str
    symbol: str
    price: float
    timestamp: datetime


# ==================== Error Response Schemas ====================
class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str
    error_code: Optional[str] = None
