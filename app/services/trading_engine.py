"""
Trading Engine for evaluating and executing pending conditional orders.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from decimal import Decimal
import logging
from datetime import datetime

from app.models import Order, OrderStatus, OrderType, OrderSide
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)

class TradingEngine:
    """Service responsible for matching pending conditional orders against live prices."""
    
    @staticmethod
    def evaluate_pending_orders(db: Session, symbol: str, current_price: float):
        """
        Evaluate all PENDING orders for a given symbol against the current price.
        Executes orders that meet their trigger conditions.
        """
        try:
            current_price_dec = Decimal(str(current_price)).quantize(Decimal('0.01'))
            
            # Find relevant pending orders
            # Use a fresh query without for_update here to avoid locking all pending orders
            pending_orders = db.query(Order).filter(
                and_(
                    Order.status == OrderStatus.PENDING,
                    Order.symbol == symbol
                )
            ).all()
            
            for order in pending_orders:
                try:
                    if TradingEngine._should_trigger(order, current_price_dec):
                        logger.info(f"Triggering order {order.id} for {symbol} at {current_price_dec}")
                        # We execute each order atomically. 
                        # execute_pending_order will acquire its own locks and manage the transaction.
                        OrderService.execute_pending_order(db, order.id, current_price_dec)
                except Exception as e:
                    logger.error(f"Failed to execute pending order {order.id}: {e}")
                    # Continue evaluating other orders even if one fails
        
        except Exception as e:
            logger.error(f"Error evaluating pending orders for {symbol}: {e}")

    @staticmethod
    def _should_trigger(order: Order, current_price: Decimal) -> bool:
        """
        Evaluate if the order's conditions are met at the current price.
        """
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                return current_price <= order.limit_price # type: ignore
            elif order.side == OrderSide.SELL:
                return current_price >= order.limit_price # type: ignore
        
        elif order.order_type == OrderType.STOP_LOSS:
            # Stop loss usually means selling if price drops below a threshold
            if order.side == OrderSide.SELL:
                return current_price <= order.stop_price # type: ignore
            elif order.side == OrderSide.BUY:
                return current_price >= order.stop_price # type: ignore
        
        return False
