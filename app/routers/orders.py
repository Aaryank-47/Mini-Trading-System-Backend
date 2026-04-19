"""
Order management API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import OrderCreate, OrderResponse, OrderHistoryResponse
from app.services.order_service import OrderService
from app.websocket import connection_manager
from datetime import datetime
from typing import List
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    responses={404: {"description": "Not found"}}
)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db)
):
    """
    Execute a new order (BUY or SELL)
    
    **BUY Logic:**
    - Fetches price from Redis
    - Checks wallet balance
    - Deducts amount from wallet
    - Updates position with weighted average price
    
    **SELL Logic:**
    - Checks if user has sufficient quantity
    - Reduces position
    - Adds money to wallet
    
    Both operations create an order record with status = COMPLETED
    """
    try:
        # Validate user exists
        from app.services.user_service import UserService
        user = UserService.get_user(db, order_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {order_data.user_id} not found"
            )
        
        # Execute order
        order = OrderService.execute_order(db, order_data)
        
        # Send WebSocket notification
        try:
            asyncio.create_task(_send_order_notification(order_data.user_id, order))
        except Exception as ws_error:
            logger.warning(f"Failed to send WebSocket notification: {ws_error}")
        
        return order
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
            headers={"error_code": "VALIDATION_ERROR"}
        )
    except Exception as e:
        logger.error(f"Order execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute order"
        )


@router.get("/{user_id}", response_model=List[OrderHistoryResponse])
def get_order_history(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get order history for a user
    
    Returns all past orders sorted by most recent first
    """
    from app.services.user_service import UserService
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    orders = OrderService.get_order_history(db, user_id, skip=skip, limit=limit)
    return orders


@router.get("/{user_id}/count")
def get_order_count(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get total order count for a user"""
    from app.services.user_service import UserService
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    orders = OrderService.get_order_history(db, user_id, limit=10000)
    return {
        "user_id": user_id,
        "total_orders": len(orders)
    }


async def _send_order_notification(user_id: int, order):
    """Send order execution notification via WebSocket"""
    message = {
        "event": "order_executed",
        "symbol": order.symbol,
        "qty": order.quantity,
        "price": order.price,
        "side": order.side.value,
        "status": order.status.value,
        "total_amount": order.total_amount,
        "timestamp": order.created_at.isoformat()
    }
    await connection_manager.broadcast_to_user(user_id, message)
