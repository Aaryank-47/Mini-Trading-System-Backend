"""
Order management API routes
✅ FIXED: Added JWT authentication and ownership verification
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import OrderCreate, OrderResponse, OrderHistoryResponse
from app.services.order_service import OrderService
from app.services.price_service import PriceService
from app.services.user_service import UserService
from app.security import get_current_user, verify_user_ownership
from app.websocket import connection_manager
from datetime import datetime
from typing import List
import logging
from starlette.concurrency import run_in_threadpool

from app.utils.rate_limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    responses={404: {"description": "Not found"}}
)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_order(
    request: Request,
    order_data: OrderCreate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ✅ FIXED: Execute a new order with authentication
    
    Requires: Bearer token in Authorization header
    
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
        verify_user_ownership(order_data.user_id, current_user_id)
        
        user = UserService.get_user(db, order_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {order_data.user_id} not found"
            )
        
        if order_data.order_type == "MARKET":
            order = await run_in_threadpool(OrderService.execute_order, db, order_data)
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order failed"
                )
            
            try:
                # Send real-time order event from the active app event loop.
                await _send_order_notification(order_data.user_id, order, event="order_executed")
            except Exception as ws_error:
                logger.warning(f"Failed to send WebSocket notification: {ws_error}")
        else:
            order = await run_in_threadpool(OrderService.create_pending_order, db, order_data)
            
            try:
                # Send real-time order event
                await _send_order_notification(order_data.user_id, order, event="order_created")
            except Exception as ws_error:
                logger.warning(f"Failed to send WebSocket notification: {ws_error}")

        response = OrderResponse.from_orm(order)
        logger.info(f"Returning order response: {response.id}")
        return response

    except HTTPException:
        # Preserve auth and validation HTTP responses (e.g., 403 ownership violations)
        raise

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
    current_user_id: int = Depends(get_current_user),
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """
    ✅ FIXED: Get order history with authentication
    
    Requires: Bearer token in Authorization header (can only access own orders)
    
    Returns all past orders sorted by most recent first
    """
    verify_user_ownership(user_id, current_user_id)
    
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

@router.delete("/{order_id}", status_code=status.HTTP_200_OK)
def cancel_order(
    order_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ✅ FIXED: Cancel a pending order
    """
    order = OrderService.get_order(db, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
        
    verify_user_ownership(order.user_id, current_user_id)
    
    if order.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be cancelled"
        )
        
    success = OrderService.cancel_order(db, order_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel order"
        )
        
    return {"success": True, "message": "Order cancelled successfully"}


@router.get("/{user_id}/pending", response_model=List[OrderHistoryResponse])
def get_pending_orders(
    user_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all pending orders for a user.
    """
    verify_user_ownership(user_id, current_user_id)
    from app.models import Order, OrderStatus
    
    orders = db.query(Order).filter(
        Order.user_id == user_id,
        Order.status == OrderStatus.PENDING
    ).order_by(Order.created_at.desc()).all()
    
    return orders


async def _send_order_notification(user_id: int, order, event: str = "order_executed"):
    """Send order execution/creation notification via WebSocket"""
    message = {
        "event": event,
        "data": {
            "id": order.id,
            "order_id": order.id,
            "user_id": user_id,
            "symbol": order.symbol,
            "symbol_name": PriceService.get_symbol_name(order.symbol, None),
            "quantity": order.quantity,
            "qty": order.quantity,
            "price": float(order.price) if order.price else None,
            "side": order.side.value if hasattr(order.side, 'value') else order.side,
            "order_type": order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
            "status": order.status.value if hasattr(order.status, 'value') else order.status,
            "total_amount": float(order.total_amount) if order.total_amount else None,
            "limit_price": float(order.limit_price) if order.limit_price else None,
            "stop_price": float(order.stop_price) if order.stop_price else None,
            "created_at": order.created_at.isoformat(),
            "timestamp": order.created_at.isoformat(),
        }
    }
    await connection_manager.broadcast_to_user(user_id, message)
