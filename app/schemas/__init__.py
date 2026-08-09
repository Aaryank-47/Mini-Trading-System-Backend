"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


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


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True


class WalletResponse(BaseModel):
    """Schema for wallet response"""
    id: int
    user_id: int
    balance: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True


class OrderCreate(BaseModel):
    """Schema for creating an order"""
    user_id: int = Field(..., gt=0)
    symbol: str = Field(..., min_length=1, max_length=10)
    qty: int = Field(..., gt=0, le=1000000)
    side: str = Field(..., pattern="^(BUY|SELL)$")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        v = v.upper()
        if not v.isalpha():
            raise ValueError('Symbol must contain only letters')
        return v


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: int
    user_id: int
    symbol: str
    quantity: int
    price: Decimal
    total_amount: Decimal
    side: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True


class OrderHistoryResponse(BaseModel):
    """Schema for order history"""
    id: int
    symbol: str
    quantity: int
    price: Decimal
    total_amount: Decimal
    side: str
    status: str
    created_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True


class PositionResponse(BaseModel):
    """Schema for position response"""
    id: int
    user_id: int
    symbol: str
    quantity: int
    average_price: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True


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


class StockResponse(BaseModel):
    """Schema for stock response"""
    id: int
    symbol: str
    company_name: str
    min_price: float
    max_price: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True


class StockListResponse(BaseModel):
    """Schema for stock list response"""
    id: int
    symbol: str
    company_name: str
    is_active: bool
    
    class Config:
        orm_mode = True
        from_attributes = True


class StockSymbolResponse(BaseModel):
    """Schema for active stock symbol"""
    symbol: str
    company_name: str
    is_active: bool
    
    class Config:
        orm_mode = True
        from_attributes = True


class ApiResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
    count: Optional[int] = None
