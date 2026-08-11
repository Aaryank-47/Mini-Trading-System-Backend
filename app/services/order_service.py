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
from app.services.audit_service import AuditService
from app.models.audit import AuditEventType, AuditEntityType
from decimal import Decimal, ROUND_HALF_UP
from typing import cast

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order management and execution"""
    
    @staticmethod
    def execute_order(db: Session, order_data: OrderCreate) -> Order:
        """
           FIXED: Execute BUY or SELL order with atomic transaction and row-level locking
        
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
            print(f"Price for symbol {symbol}: {price}")
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
            
            # Log failed order attempt
            AuditService.log(
                db=db,
                event_type=AuditEventType.ORDER_FAILED,
                entity_type=AuditEntityType.ORDER,
                entity_id=None,
                user_id=user_id,
                status="FAILED",
                metadata_info={"symbol": symbol, "quantity": quantity, "side": side, "reason": str(e)},
                commit=True
            )
            
            raise

    @staticmethod
    def create_pending_order(db: Session, order_data: OrderCreate) -> Order:
        """Create a new pending conditional order without executing it."""
        from app.models import OrderType
        order = Order(
            user_id=order_data.user_id,
            symbol=order_data.symbol.upper(),
            quantity=order_data.qty,
            order_type=OrderType(order_data.order_type),
            limit_price=order_data.limit_price,
            stop_price=order_data.stop_price,
            side=OrderSide(order_data.side.upper()),
            status=OrderStatus.PENDING
        )
        db.add(order)
        db.flush()
        
        event_type = AuditEventType.LIMIT_ORDER_CREATED if order.order_type == OrderType.LIMIT else AuditEventType.STOP_LOSS_CREATED
        
        AuditService.log(
            db=db,
            event_type=event_type,
            entity_type=AuditEntityType.ORDER,
            entity_id=cast(int, order.id),
            user_id=cast(int, order.user_id),
            status="SUCCESS",
            metadata_info={
                "symbol": order.symbol, 
                "quantity": order.quantity, 
                "side": order.side.value,
                "limit_price": float(cast(Decimal, order.limit_price)) if order.limit_price else None,
                "stop_price": float(cast(Decimal, order.stop_price)) if order.stop_price else None
            },
            commit=False
        )
        
        db.commit()
        db.refresh(order)
        logger.info(f"✓ Created PENDING {order.order_type.value} order {order.id} for {order.symbol}")
        return order

    @staticmethod
    def execute_pending_order(db: Session, order_id: int, execution_price: Decimal) -> Order:
        """Idempotently execute a pending order at the given execution price."""
        try:
            # 1. Lock the order row to prevent duplicate execution
            order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
            if not order:
                db.rollback()
                raise ValueError(f"Order {order_id} not found")
            
            # 2. Idempotency check: Ensure it's still PENDING
            if order.status != OrderStatus.PENDING:
                logger.info(f"Order {order_id} already processed (status: {order.status})")
                db.rollback()
                return order
            
            # 3. Execute
            total_amount = Decimal(order.quantity) * execution_price
            
            if order.side == OrderSide.BUY:
                executed_order = OrderService._execute_buy_order(
                    db, order.user_id, order.symbol, order.quantity, execution_price, total_amount, existing_order=order
                )
            else:
                executed_order = OrderService._execute_sell_order(
                    db, order.user_id, order.symbol, order.quantity, execution_price, total_amount, existing_order=order
                )
                
            # WebSocket notification logic is decoupled and handled by the caller or a separate pub/sub mechanism
            return executed_order
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to execute pending order {order_id}: {e}")
            
            # Optional: Mark as FAILED if it was a persistent error, but for now we just rollback
            # order.status = OrderStatus.FAILED
            # db.commit()
            
            raise
    
    @staticmethod
    def _execute_buy_order(db: Session, user_id: int, symbol: str,
                          quantity: int, price: Decimal, total_amount: Decimal, existing_order: Order = None) -> Order:
        """
         FIXED: Execute BUY order with atomic transaction
        
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
            
            AuditService.log(
                db=db,
                event_type=AuditEventType.WALLET_DEBITED,
                entity_type=AuditEntityType.WALLET,
                entity_id=cast(int, wallet.id),
                user_id=user_id,
                status="SUCCESS",
                metadata_info={"amount": float(total_amount), "reason": f"Buy order for {symbol}"},
                commit=False
            )
            
            # ✅ FIXED: Lock position row to prevent concurrent updates
            position = db.query(Position).filter(
                and_(
                    Position.user_id == user_id,
                    Position.symbol == symbol
                )
            ).with_for_update().first()
            
            if position:
                # Calculate weighted average price
                total_cost = (Decimal(position.quantity) * position.average_price) + (Decimal(quantity) * price)  # type: ignore
                total_qty = position.quantity + quantity
                
                prev_state = {"quantity": position.quantity, "average_price": float(cast(Decimal, position.average_price))}
                
                position.average_price = (total_cost / Decimal(total_qty)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)  # type: ignore
                position.quantity = total_qty  # type: ignore
                
                AuditService.log(
                    db=db,
                    event_type=AuditEventType.POSITION_UPDATED,
                    entity_type=AuditEntityType.POSITION,
                    entity_id=cast(int, position.id),
                    user_id=user_id,
                    status="SUCCESS",
                    previous_state=prev_state,
                    new_state={"quantity": position.quantity, "average_price": float(cast(Decimal, position.average_price))},
                    commit=False
                )
            else:
                # Create new position
                position = Position(
                    user_id=user_id,
                    symbol=symbol,
                    quantity=quantity,
                    average_price=price
                )
                db.add(position)
                db.flush()
                
                AuditService.log(
                    db=db,
                    event_type=AuditEventType.POSITION_CREATED,
                    entity_type=AuditEntityType.POSITION,
                    entity_id=cast(int, position.id),
                    user_id=user_id,
                    status="SUCCESS",
                    new_state={"quantity": position.quantity, "average_price": float(cast(Decimal, position.average_price))},
                    commit=False
                )
            
            # Update or create order record
            from app.models import OrderType
            if existing_order:
                existing_order.price = price
                existing_order.total_amount = total_amount
                existing_order.status = OrderStatus.COMPLETED
                existing_order.executed_at = datetime.utcnow()
                order = existing_order
            else:
                order = Order(
                    user_id=user_id,
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    total_amount=total_amount,
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    status=OrderStatus.COMPLETED,
                    executed_at=datetime.utcnow()
                )
                db.add(order)
            
            db.flush()
            
            from app.models import OrderType
            event_type = AuditEventType.ORDER_EXECUTED
            if order.order_type == OrderType.LIMIT:
                event_type = AuditEventType.LIMIT_ORDER_EXECUTED
            elif order.order_type == OrderType.STOP_LOSS:
                event_type = AuditEventType.STOP_LOSS_EXECUTED
            
            if not existing_order:
                # Log creation for market orders explicitly in the same transaction
                AuditService.log(
                    db=db,
                    event_type=AuditEventType.ORDER_CREATED,
                    entity_type=AuditEntityType.ORDER,
                    entity_id=cast(int, order.id),
                    user_id=user_id,
                    status="SUCCESS",
                    metadata_info={"symbol": symbol, "quantity": quantity, "side": "BUY", "order_type": "MARKET"},
                    commit=False
                )
            
            AuditService.log(
                db=db,
                event_type=event_type,
                entity_type=AuditEntityType.ORDER,
                entity_id=cast(int, order.id),
                user_id=user_id,
                status="SUCCESS",
                metadata_info={
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": float(price),
                    "total_amount": float(total_amount),
                    "side": "BUY"
                },
                commit=False
            )
            
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
                           quantity: int, price: Decimal, total_amount: Decimal, existing_order: Order = None) -> Order:
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
            prev_state = {"quantity": position.quantity, "average_price": float(cast(Decimal, position.average_price))}
            position.quantity -= quantity
            
            if position.quantity == 0:
                # Delete position if quantity becomes 0
                db.delete(position)
                AuditService.log(
                    db=db,
                    event_type=AuditEventType.POSITION_CLOSED,
                    entity_type=AuditEntityType.POSITION,
                    entity_id=cast(int, position.id),
                    user_id=user_id,
                    status="SUCCESS",
                    previous_state=prev_state,
                    commit=False
                )
            else:
                AuditService.log(
                    db=db,
                    event_type=AuditEventType.POSITION_UPDATED,
                    entity_type=AuditEntityType.POSITION,
                    entity_id=cast(int, position.id),
                    user_id=user_id,
                    status="SUCCESS",
                    previous_state=prev_state,
                    new_state={"quantity": position.quantity, "average_price": float(cast(Decimal, position.average_price))},
                    commit=False
                )
            
            # ✅ FIXED: Lock wallet row
            wallet = db.query(Wallet).filter(
                Wallet.user_id == user_id
            ).with_for_update().first()
            
            if not wallet:
                raise ValueError(f"Wallet not found for user {user_id}")
            
            # Add to wallet
            wallet.balance += total_amount
            
            AuditService.log(
                db=db,
                event_type=AuditEventType.WALLET_CREDITED,
                entity_type=AuditEntityType.WALLET,
                entity_id=cast(int, wallet.id),
                user_id=user_id,
                status="SUCCESS",
                metadata_info={"amount": float(total_amount), "reason": f"Sell order for {symbol}"},
                commit=False
            )
            
            # Update or create order record
            from app.models import OrderType
            if existing_order:
                existing_order.price = price
                existing_order.total_amount = total_amount
                existing_order.status = OrderStatus.COMPLETED
                existing_order.executed_at = datetime.utcnow()
                order = existing_order
            else:
                order = Order(
                    user_id=user_id,
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    total_amount=total_amount,
                    order_type=OrderType.MARKET,
                    side=OrderSide.SELL,
                    status=OrderStatus.COMPLETED,
                    executed_at=datetime.utcnow()
                )
                db.add(order)
            
            db.flush()
            
            from app.models import OrderType
            event_type = AuditEventType.ORDER_EXECUTED
            if order.order_type == OrderType.LIMIT:
                event_type = AuditEventType.LIMIT_ORDER_EXECUTED
            elif order.order_type == OrderType.STOP_LOSS:
                event_type = AuditEventType.STOP_LOSS_EXECUTED
            
            if not existing_order:
                # Log creation for market orders explicitly in the same transaction
                AuditService.log(
                    db=db,
                    event_type=AuditEventType.ORDER_CREATED,
                    entity_type=AuditEntityType.ORDER,
                    entity_id=cast(int, order.id),
                    user_id=user_id,
                    status="SUCCESS",
                    metadata_info={"symbol": symbol, "quantity": quantity, "side": "SELL", "order_type": "MARKET"},
                    commit=False
                )
            
            AuditService.log(
                db=db,
                event_type=event_type,
                entity_type=AuditEntityType.ORDER,
                entity_id=cast(int, order.id),
                user_id=user_id,
                status="SUCCESS",
                metadata_info={
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": float(price),
                    "total_amount": float(total_amount),
                    "side": "SELL"
                },
                commit=False
            )
            
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
        
        from app.models import OrderType
        event_type = AuditEventType.ORDER_CANCELLED
        if order.order_type == OrderType.LIMIT:
            event_type = AuditEventType.LIMIT_ORDER_CANCELLED
        elif order.order_type == OrderType.STOP_LOSS:
            event_type = AuditEventType.STOP_LOSS_CANCELLED
            
        AuditService.log(
            db=db,
            event_type=event_type,
            entity_type=AuditEntityType.ORDER,
            entity_id=cast(int, order.id),
            user_id=cast(int, order.user_id),
            status="SUCCESS",
            commit=False
        )
        
        db.commit()
        logger.info(f"✓ Order cancelled: {order_id}")
        return True
