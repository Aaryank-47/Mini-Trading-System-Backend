"""
Portfolio and position API routes
✅ FIXED: Added JWT authentication and authorization
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import get_db
from app.schemas import PortfolioResponse, PortfolioItem
from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from app.services.position_service import PositionService
from app.utils.redis_manager import get_price
from app.security import get_current_user, verify_user_ownership  # ✅ NEW: Import auth
from typing import List

router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"],
    responses={404: {"description": "Not found"}}
)


@router.get("/{user_id}", response_model=PortfolioResponse)
def get_portfolio(
    user_id: int,
    current_user_id: int = Depends(get_current_user),  # ✅ FIXED: Require authentication
    db: Session = Depends(get_db)
):
    """
    ✅ FIXED: Get complete portfolio for a user (requires authentication)
    
    Requires: Bearer token in Authorization header (can only access own portfolio)
    
    Returns:
    - All holdings with current prices
    - Unrealized P&L per position
    - Total portfolio value
    - Total unrealized P&L
    """
    # ✅ FIXED: Verify user is accessing their own portfolio
    verify_user_ownership(user_id, current_user_id)
    
    # Validate user exists
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Get wallet balance
    wallet = WalletService.get_wallet(db, user_id)
    wallet_balance = wallet.balance if wallet else 0.0
    
    # Get all positions
    positions = PositionService.get_all_positions(db, user_id)
    
    holdings = []
    total_invested = 0.0
    total_current_value = 0.0
    total_unrealized_pnl = 0.0
    
    for position in positions:
        current_price = get_price(position.symbol)
        if current_price is None:
            continue
        
        total_invested_in_position = position.quantity * position.average_price
        current_value = position.quantity * current_price
        unrealized_pnl = current_value - total_invested_in_position
        
        pnl_percentage = 0.0
        if total_invested_in_position > 0:
            pnl_percentage = (unrealized_pnl / total_invested_in_position) * 100
        
        holdings.append(PortfolioItem(
            symbol=position.symbol,
            quantity=position.quantity,
            average_price=position.average_price,
            current_price=current_price,
            total_invested=total_invested_in_position,
            current_value=current_value,
            unrealized_pnl=unrealized_pnl,
            pnl_percentage=pnl_percentage
        ))
        
        total_invested += total_invested_in_position
        total_current_value += current_value
        total_unrealized_pnl += unrealized_pnl
    
    total_portfolio_value = float(wallet_balance) + total_current_value
    total_pnl_percentage = 0.0
    if total_invested > 0:
        total_pnl_percentage = (total_unrealized_pnl / total_invested) * 100
    
    return PortfolioResponse(
        user_id=user_id,
        wallet_balance=wallet_balance,
        holdings=holdings,
        total_portfolio_value=total_portfolio_value,
        total_invested=total_invested,
        total_unrealized_pnl=total_unrealized_pnl,
        total_pnl_percentage=total_pnl_percentage
    )


@router.get("/{user_id}/positions", response_model=List[PortfolioItem])
def get_positions(
    user_id: int,
    current_user_id: int = Depends(get_current_user),  # ✅ FIXED: Require authentication
    db: Session = Depends(get_db)
):
    """
    ✅ FIXED: Get all open positions for a user (requires authentication)
    
    Requires: Bearer token in Authorization header (can only access own positions)
    """
    # ✅ FIXED: Verify user is accessing their own positions
    verify_user_ownership(user_id, current_user_id)
    
    # Validate user exists
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    positions = PositionService.get_all_positions(db, user_id)
    
    holdings = []
    for position in positions:
        current_price = get_price(position.symbol)
        if current_price is None:
            continue
        
        # Convert current_price to Decimal to match position.average_price type
        current_price_decimal = Decimal(str(current_price))
        
        total_invested_in_position = position.quantity * position.average_price
        current_value = position.quantity * current_price_decimal
        unrealized_pnl = current_value - total_invested_in_position
        
        pnl_percentage = 0.0
        if total_invested_in_position > 0:
            pnl_percentage = (unrealized_pnl / total_invested_in_position) * 100
        
        holdings.append(PortfolioItem(
            symbol=position.symbol,
            quantity=position.quantity,
            average_price=position.average_price,
            current_price=current_price_decimal,
            total_invested=total_invested_in_position,
            current_value=current_value,
            unrealized_pnl=unrealized_pnl,
            pnl_percentage=pnl_percentage
        ))
    
    return holdings


@router.get("/{user_id}/balance")
def get_wallet_balance(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get current wallet balance for a user"""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    balance = WalletService.get_balance(db, user_id)
    return {
        "user_id": user_id,
        "balance": balance,
        "currency": "INR"
    }
