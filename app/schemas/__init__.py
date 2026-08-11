"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from .audit import AuditLogResponse, PaginatedAuditLogs
class ORMBase(BaseModel):
    """Base model for ORM schema conversions"""
    class Config: # type: ignore
        orm_mode = True
        from_attributes = True


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password with uppercase, lowercase, digit, and special character")
    confirm_password: str = Field(..., min_length=8)
    
    @validator('name')
    def validate_name(cls, v):
        if any(char in v for char in ['<', '>', '"', "'"]):
            raise ValueError('Name contains invalid characters')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        from app.utils.password import validate_password_strength
        error = validate_password_strength(v)
        if error:
            raise ValueError(error)
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_passwords_match(cls, values):
        """Validate password confirmation matches"""
        if values.get('password') != values.get('confirm_password'):
            raise ValueError('Passwords do not match')
        return values


class UserResponse(ORMBase):
    """Schema for user response"""
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: datetime


class WalletResponse(ORMBase):
    """Schema for wallet response"""
    id: int
    user_id: int
    balance: Decimal
    created_at: datetime
    updated_at: datetime


class OrderCreate(BaseModel):
    """Schema for creating an order"""
    user_id: int = Field(..., gt=0)
    symbol: str = Field(..., min_length=1, max_length=10)
    qty: int = Field(..., gt=0, le=1000000)
    side: str = Field(..., regex="^(BUY|SELL)$")
    order_type: str = Field(default="MARKET", regex="^(MARKET|LIMIT|STOP_LOSS)$")
    limit_price: Optional[Decimal] = Field(None, gt=Decimal('0'))  # type: ignore
    stop_price: Optional[Decimal] = Field(None, gt=Decimal('0'))  # type: ignore
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v.isupper():
            raise ValueError('Symbol must be uppercase')
        if not v.isalpha():
            raise ValueError('Symbol must contain only letters')
        return v

    @root_validator(skip_on_failure=True)
    def validate_order_type_prices(cls, values):
        order_type = values.get('order_type')
        limit_price = values.get('limit_price')
        stop_price = values.get('stop_price')
        
        if order_type == 'MARKET':
            if limit_price is not None or stop_price is not None:
                raise ValueError("MARKET orders cannot have limit_price or stop_price")
        elif order_type == 'LIMIT':
            if limit_price is None:
                raise ValueError("LIMIT orders must have a limit_price")
            if stop_price is not None:
                raise ValueError("LIMIT orders cannot have a stop_price")
        elif order_type == 'STOP_LOSS':
            if stop_price is None:
                raise ValueError("STOP_LOSS orders must have a stop_price")
            if limit_price is not None:
                raise ValueError("STOP_LOSS orders cannot have a limit_price")
        
        return values


class OrderResponse(ORMBase):
    """Schema for order response"""
    id: int
    user_id: int
    symbol: str
    quantity: int
    order_type: str
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    price: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    side: str
    status: str
    triggered_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class OrderHistoryResponse(ORMBase):
    """Schema for order history"""
    id: int
    symbol: str
    quantity: int
    order_type: str
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    price: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    side: str
    status: str
    triggered_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    created_at: datetime


class PositionResponse(ORMBase):
    """Schema for position response"""
    id: int
    user_id: int
    symbol: str
    quantity: int
    average_price: Decimal
    created_at: datetime
    updated_at: datetime


class PortfolioItem(BaseModel):
    """Schema for a portfolio holding"""
    symbol: str
    quantity: int
    average_price: Decimal
    current_price: Decimal
    total_invested: Decimal
    current_value: Decimal
    unrealized_pnl: Decimal
    pnl_percentage: Decimal


class PortfolioResponse(BaseModel):
    """Schema for full portfolio response"""
    user_id: int
    wallet_balance: Decimal
    holdings: List[PortfolioItem]
    total_portfolio_value: Decimal
    total_invested: Decimal
    total_unrealized_pnl: Decimal
    total_pnl_percentage: Decimal


class LoginRequest(BaseModel):
    """Schema for user login request"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for JWT token response (registration/login)"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: Optional[str] = None
    email: Optional[str] = None


class AccessTokenResponse(BaseModel):
    """Schema for access token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    expires_in: int  # Seconds
    name: Optional[str] = None
    email: Optional[str] = None


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response"""
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds


class LoginResponse(BaseModel):
    """Schema for complete login response with both tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    expires_in: int
    email: Optional[str] = None


class OrderExecutedMessage(BaseModel):
    """Schema for WebSocket order executed message"""
    event: str
    symbol: str
    qty: int
    price: Decimal
    side: str
    status: str
    total_amount: Decimal
    timestamp: datetime


class PriceUpdateMessage(BaseModel):
    """Schema for WebSocket price update message"""
    event: str
    symbol: str
    price: Decimal
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str
    error_code: Optional[str] = None


class StockCreate(BaseModel):
    """Schema for creating a new stock"""
    symbol: str = Field(..., min_length=1, max_length=20)
    company_name: str = Field(..., min_length=1, max_length=255)
    min_price: float = Field(..., gt=0)
    max_price: float = Field(..., gt=0)
    is_active: bool = Field(default=True)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        v = v.upper()
        if not v.isalpha():
            raise ValueError('Symbol must contain only letters')
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_prices(cls, values):
        """Validate that min_price is less than max_price"""
        min_price = values.get('min_price')
        max_price = values.get('max_price')
        if min_price and max_price and min_price >= max_price:
            raise ValueError('min_price must be less than max_price')
        return values


class StockUpdate(BaseModel):
    """Schema for updating a stock"""
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    min_price: Optional[float] = Field(None, gt=0)
    max_price: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None
    
    @root_validator(skip_on_failure=True)
    def validate_prices(cls, values):
        """Validate that min_price is less than max_price if both provided"""
        min_price = values.get('min_price')
        max_price = values.get('max_price')
        if min_price and max_price and min_price >= max_price:
            raise ValueError('min_price must be less than max_price')
        return values


class StockResponse(ORMBase):
    """Schema for stock response"""
    id: int
    symbol: str
    company_name: str
    min_price: float
    max_price: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StockListResponse(ORMBase):
    """Schema for stock list response"""
    id: int
    symbol: str
    company_name: str
    is_active: bool


class StockSymbolResponse(ORMBase):
    """Schema for active stock symbol"""
    symbol: str
    company_name: str
    is_active: bool


class ApiResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
    count: Optional[int] = None
