"""
Wallet service for managing wallet operations
"""
from sqlalchemy.orm import Session
from typing import cast, Optional
from app.models import Wallet, User
from app.schemas import WalletResponse
from decimal import Decimal, ROUND_HALF_UP
import logging
from app.services.audit_service import AuditService
from app.models.audit import AuditEventType, AuditEntityType

logger = logging.getLogger(__name__)


class WalletService:
    """Service for wallet management operations"""
    
    @staticmethod
    def get_wallet(db: Session, user_id: int) -> Optional[Wallet]:
        """
        Get wallet for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Wallet object or None
        """
        return db.query(Wallet).filter(Wallet.user_id == user_id).first()
    
    @staticmethod
    def get_balance(db: Session, user_id: int) -> Optional[Decimal]:
        """
        Get current wallet balance
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Balance amount as Decimal or None
        """
        wallet = WalletService.get_wallet(db, user_id)
        return cast(Decimal, wallet.balance) if wallet else None
    
    @staticmethod
    def deduct_balance(db: Session, user_id: int, amount: float) -> bool:
        """
        ✅ FIXED: Deduct amount from wallet with row-level locking
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to deduct
            
        Returns:
            True if successful, False if insufficient balance
        """
        # FIXED: Convert to Decimal with proper rounding
        dec_amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # FIXED: Use with_for_update() for row-level locking (atomic)
        wallet = db.query(Wallet).filter(
            Wallet.user_id == user_id
        ).with_for_update().first()
        
        if not wallet:
            raise ValueError(f"Wallet not found for user {user_id}")
        
        if wallet.balance < dec_amount:
            logger.warning(f"Insufficient balance for user {user_id}: {wallet.balance} < {dec_amount}")
            return False
        
        wallet.balance -= dec_amount
        
        AuditService.log(
            db=db,
            event_type=AuditEventType.WALLET_DEBITED,
            entity_type=AuditEntityType.WALLET,
            entity_id=cast(int, wallet.id),
            user_id=user_id,
            status="SUCCESS",
            metadata_info={"amount": float(amount), "reason": "Manual deduction"},
            commit=False
        )
        
        db.commit()
        logger.info(f"✓ Balance deducted: {user_id}, Amount: {amount}")
        return True
    
    @staticmethod
    def add_balance(db: Session, user_id: int, amount: float) -> bool:
        """
        ✅ FIXED: Add amount to wallet with row-level locking
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to add
            
        Returns:
            True if successful
        """
        # FIXED: Convert to Decimal with proper rounding
        dec_amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # ✅ FIXED: Use with_for_update() for row-level locking
        wallet = db.query(Wallet).filter(
            Wallet.user_id == user_id
        ).with_for_update().first()
        
        if not wallet:
            raise ValueError(f"Wallet not found for user {user_id}")
        
        wallet.balance += dec_amount
        
        AuditService.log(
            db=db,
            event_type=AuditEventType.WALLET_CREDITED,
            entity_type=AuditEntityType.WALLET,
            entity_id=cast(int, wallet.id),
            user_id=user_id,
            status="SUCCESS",
            metadata_info={"amount": float(amount), "reason": "Manual addition"},
            commit=False
        )
        
        db.commit()
        logger.info(f"✓ Balance added: {user_id}, Amount: {amount}")
        return True
    
    @staticmethod
    def check_sufficient_balance(db: Session, user_id: int, required_amount: float) -> bool:
        """
        Check if user has sufficient balance
        
        Args:
            db: Database session
            user_id: User ID
            required_amount: Amount required
            
        Returns:
            True if sufficient, False otherwise
        """
        balance = WalletService.get_balance(db, user_id)
        return balance is not None and balance >= required_amount
