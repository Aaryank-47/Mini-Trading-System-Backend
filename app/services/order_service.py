"""
Order service for managing order execution
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Order, OrderSide, OrderStatus, Position, Wallet
from app.schemas import OrderCreate, OrderResponse
from app.services.wallet_service import WalletService
from app.services.position_service import PositionService
from app.utils.redis_manager import get_price
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order management and execution"""
    
    @staticmethod
    def execute_order(db: Session, order_data: OrderCreate) -> Order:
        """
        ✅ FIXED: Execute BUY or SELL order with atomic transaction and row-level locking
        
        Args:
            db: Database session
            order_data: Order creation data
            
        Returns:
            Executed order object
        """
        user_id = order_data.user_id
        symbol = order_data.symbol.upper()
        quantity = order_data.qty
        side = order_data.side.upper()
        
        try:
            # Get current price from Redis
            price = get_price(symbol)
            if price is None:
                raise ValueError(f"Price not available for symbol {symbol}")
            
            # ✅ FIXED: Convert to Decimal with proper rounding
            price = Decimal(str(price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_amount = Decimal(str(quantity)) * price
            
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
        
        except Exception as e:
            # ✅ FIXED: Rollback on any error
            db.rollback()
            logger.error(f"Order execution failed for user {user_id}: {e}")
            raise
    
    @staticmethod
    def _execute_buy_order(db: Session, user_id: int, symbol: str,
                          quantity: int, price: Decimal, total_amount: Decimal) -> Order:
        """
        ✅ FIXED: Execute BUY order with atomic transaction
        
        - Uses with_for_update() for row-level locking
        - All operations in single transaction
        - Rollback on error
        
        Args:
            db: Database session
            user_id: User ID
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share (Decimal)
            total_amount: Total cost (Decimal)
            
        Returns:
            Executed order object
        """
        try:
            # ✅ FIXED: Lock wallet row to prevent race conditions
            wallet = db.query(Wallet).filter(
                Wallet.user_id == user_id
            ).with_for_update().first()
            
            if not wallet:
                raise ValueError(f"Wallet not found for user {user_id}")
            
            if wallet.balance < total_amount:
                raise ValueError("Insufficient balance for this order")
            
            # Deduct from wallet (same transaction)
            wallet.balance -= total_amount
            
            # ✅ FIXED: Lock position row to prevent concurrent updates
            position = db.query(Position).filter(
                and_(
                    Position.user_id == user_id,
                    Position.symbol == symbol
                )
            ).with_for_update().first()
            
            if position:
                # Calculate weighted average price
                total_cost = (Decimal(position.quantity) * position.average_price) + (Decimal(quantity) * price)
                total_qty = position.quantity + quantity
                position.average_price = (total_cost / Decimal(total_qty)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                position.quantity = total_qty
            else:
                # Create new position
                position = Position(
                    user_id=user_id,
                    symbol=symbol,
                    quantity=quantity,
                    average_price=price
                )
                db.add(position)
            
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
            
            # ✅ FIXED: Single atomic commit - all or nothing
            db.commit()
            db.refresh(order)
            
            logger.info(f"✓ BUY Order executed: user={user_id}, symbol={symbol}, qty={quantity}, price={price}")
            return order
        
        except Exception as e:
            db.rollback()
            logger.error(f"BUY Order failed for user {user_id}: {e}")
            raise
    
    @staticmethod
    def _execute_sell_order(db: Session, user_id: int, symbol: str,
                           quantity: int, price: Decimal, total_amount: Decimal) -> Order:
        """
        ✅ FIXED: Execute SELL order with atomic transaction
        
        - Uses with_for_update() for row-level locking
        - All operations in single transaction
        - Rollback on error
        
        Args:
            db: Database session
            user_id: User ID
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share (Decimal)
            total_amount: Total proceeds (Decimal)
            
        Returns:
            Executed order object
        """
        try:
            # ✅ FIXED: Lock position row to prevent concurrent sells
            position = db.query(Position).filter(
                and_(
                    Position.user_id == user_id,
                    Position.symbol == symbol
                )
            ).with_for_update().first()
            
            if not position or position.quantity < quantity:
                raise ValueError(f"Insufficient quantity to sell for {symbol}")
            
            # Reduce position
            position.quantity -= quantity
            
            if position.quantity == 0:
                # Delete position if quantity becomes 0
                db.delete(position)
            
            # ✅ FIXED: Lock wallet row
            wallet = db.query(Wallet).filter(
                Wallet.user_id == user_id
            ).with_for_update().first()
            
            if not wallet:
                raise ValueError(f"Wallet not found for user {user_id}")
            
            # Add to wallet
            wallet.balance += total_amount
            
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
            
            # ✅ FIXED: Single atomic commit - all or nothing
            db.commit()
            db.refresh(order)
            
            logger.info(f"✓ SELL Order executed: user={user_id}, symbol={symbol}, qty={quantity}, price={price}")
            return order
        
        except Exception as e:
            db.rollback()
            logger.error(f"SELL Order failed for user {user_id}: {e}")
            raise
    
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
