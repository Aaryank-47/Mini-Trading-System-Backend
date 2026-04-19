"""
Order service for managing order execution
"""
from sqlalchemy.orm import Session
from app.models import Order, OrderSide, OrderStatus, Position
from app.schemas import OrderCreate, OrderResponse
from app.services.wallet_service import WalletService
from app.services.position_service import PositionService
from app.utils.redis_manager import get_price
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order management and execution"""
    
    @staticmethod
    def execute_order(db: Session, order_data: OrderCreate) -> Order:
        """
        Execute BUY or SELL order
        
        Args:
            db: Database session
            order_data: Order creation data
            
        Returns:
            Executed order object
        """
        user_id = order_data.user_id
        symbol = order_data.symbol
        quantity = order_data.qty
        side = order_data.side
        
        # Get current price from Redis
        price = get_price(symbol)
        if price is None:
            raise ValueError(f"Price not available for symbol {symbol}")
        
        total_amount = price * quantity
        
        if side == "BUY":
            return OrderService._execute_buy_order(
                db, user_id, symbol, quantity, price, total_amount
            )
        elif side == "SELL":
            return OrderService._execute_sell_order(
                db, user_id, symbol, quantity, price, total_amount
            )
        else:
            raise ValueError(f"Invalid order side: {side}")
    
    @staticmethod
    def _execute_buy_order(db: Session, user_id: int, symbol: str,
                          quantity: int, price: float, total_amount: float) -> Order:
        """
        Execute BUY order
        
        Args:
            db: Database session
            user_id: User ID
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share
            total_amount: Total cost
            
        Returns:
            Executed order object
        """
        # Check sufficient balance
        if not WalletService.check_sufficient_balance(db, user_id, total_amount):
            raise ValueError("Insufficient balance for this order")
        
        # Deduct from wallet
        WalletService.deduct_balance(db, user_id, total_amount)
        
        # Update position
        PositionService.update_position_on_buy(db, user_id, symbol, quantity, price)
        
        # Create order record
        order = Order(
            user_id=user_id,
            symbol=symbol,
            quantity=quantity,
            price=price,
            total_amount=total_amount,
            side=OrderSide.BUY,
            status=OrderStatus.COMPLETED
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        logger.info(f"✓ BUY Order executed: user={user_id}, symbol={symbol}, qty={quantity}, price={price}")
        return order
    
    @staticmethod
    def _execute_sell_order(db: Session, user_id: int, symbol: str,
                           quantity: int, price: float, total_amount: float) -> Order:
        """
        Execute SELL order
        
        Args:
            db: Database session
            user_id: User ID
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share
            total_amount: Total proceeds
            
        Returns:
            Executed order object
        """
        # Check sufficient quantity
        if not PositionService.check_sufficient_quantity(db, user_id, symbol, quantity):
            raise ValueError(f"Insufficient quantity to sell for {symbol}")
        
        # Reduce position
        PositionService.update_position_on_sell(db, user_id, symbol, quantity)
        
        # Add to wallet
        WalletService.add_balance(db, user_id, total_amount)
        
        # Create order record
        order = Order(
            user_id=user_id,
            symbol=symbol,
            quantity=quantity,
            price=price,
            total_amount=total_amount,
            side=OrderSide.SELL,
            status=OrderStatus.COMPLETED
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        logger.info(f"✓ SELL Order executed: user={user_id}, symbol={symbol}, qty={quantity}, price={price}")
        return order
    
    @staticmethod
    def get_order(db: Session, order_id: int) -> Order:
        """
        Get order by ID
        
        Args:
            db: Database session
            order_id: Order ID
            
        Returns:
            Order object or None
        """
        return db.query(Order).filter(Order.id == order_id).first()
    
    @staticmethod
    def get_order_history(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list:
        """
        Get order history for a user
        
        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of orders
        """
        return db.query(Order).filter(
            Order.user_id == user_id
        ).order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def cancel_order(db: Session, order_id: int) -> bool:
        """
        Cancel a pending order
        
        Args:
            db: Database session
            order_id: Order ID
            
        Returns:
            True if cancelled, False if not found or already completed
        """
        order = OrderService.get_order(db, order_id)
        if not order:
            return False
        
        if order.status == OrderStatus.COMPLETED:
            return False
        
        order.status = OrderStatus.CANCELLED
        db.commit()
        logger.info(f"✓ Order cancelled: {order_id}")
        return True
