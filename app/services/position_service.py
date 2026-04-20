"""
Position service for managing user holdings
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Position
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)


class PositionService:
    """Service for position management operations"""
    
    @staticmethod
    def get_position(db: Session, user_id: int, symbol: str) -> Optional[Position]:
        """
        Get position for a user and symbol
        
        Args:
            db: Database session
            user_id: User ID
            symbol: Stock symbol
            
        Returns:
            Position object or None
        """
        return db.query(Position).filter(
            Position.user_id == user_id,
            Position.symbol == symbol
        ).first()
    
    @staticmethod
    def get_all_positions(db: Session, user_id: int) -> list:
        """
        Get all positions for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            List of positions
        """
        return db.query(Position).filter(Position.user_id == user_id).all()
    
    @staticmethod
    def create_position(db: Session, user_id: int, symbol: str, 
                       quantity: int, price: float) -> Position:
        """
        Create a new position
        
        Args:
            db: Database session
            user_id: User ID
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share
            
        Returns:
            Created position object
        """
        position = Position(
            user_id=user_id,
            symbol=symbol,
            quantity=quantity,
            average_price=price
        )
        db.add(position)
        db.commit()
        logger.info(f"✓ Position created: user={user_id}, symbol={symbol}, qty={quantity}")
        return position
    
    @staticmethod
    def update_position_on_buy(db: Session, user_id: int, symbol: str,
                              quantity: int, price: Decimal) -> Position:
        """
        ✅ FIXED: Update position on BUY order with weighted average price calculation
        
        - Uses Decimal for precision
        - Uses with_for_update() for row-level locking
        
        Args:
            db: Database session
            user_id: User ID
            symbol: Stock symbol
            quantity: Number of shares to buy
            price: Price per share (Decimal)
            
        Returns:
            Updated position object
        """
        # ✅ FIXED: Use with_for_update() for row-level locking
        position = db.query(Position).filter(
            and_(
                Position.user_id == user_id,
                Position.symbol == symbol
            )
        ).with_for_update().first()
        
        if position:
            # ✅ FIXED: Use Decimal arithmetic with proper rounding
            total_cost = (Decimal(position.quantity) * position.average_price) + (Decimal(quantity) * price)
            total_quantity = position.quantity + quantity
            position.average_price = (total_cost / Decimal(total_quantity)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            position.quantity = total_quantity
        else:
            # Create new position
            return PositionService.create_position(db, user_id, symbol, quantity, price)
        
        db.commit()
        logger.info(f"✓ Position updated on BUY: user={user_id}, symbol={symbol}, qty={position.quantity}")
        return position
    
    @staticmethod
    def update_position_on_sell(db: Session, user_id: int, symbol: str,
                               quantity: int) -> Optional[Position]:
        """
        Update position on SELL order (reduce quantity)
        
        Args:
            db: Database session
            user_id: User ID
            symbol: Stock symbol
            quantity: Number of shares to sell
            
        Returns:
            Updated position object or None
        """
        position = PositionService.get_position(db, user_id, symbol)
        
        if not position or position.quantity < quantity:
            return None
        
        position.quantity -= quantity
        
        # Delete position if quantity becomes 0
        if position.quantity == 0:
            db.delete(position)
            logger.info(f"✓ Position deleted: user={user_id}, symbol={symbol}")
        else:
            logger.info(f"✓ Position updated on SELL: user={user_id}, symbol={symbol}, qty={position.quantity}")
        
        db.commit()
        return position
    
    @staticmethod
    def check_sufficient_quantity(db: Session, user_id: int, symbol: str,
                                 required_quantity: int) -> bool:
        """
        Check if user has sufficient quantity to sell
        
        Args:
            db: Database session
            user_id: User ID
            symbol: Stock symbol
            required_quantity: Quantity required
            
        Returns:
            True if sufficient, False otherwise
        """
        position = PositionService.get_position(db, user_id, symbol)
        return position is not None and position.quantity >= required_quantity
