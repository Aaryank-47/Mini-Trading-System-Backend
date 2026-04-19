"""
Wallet service for managing wallet operations
"""
from sqlalchemy.orm import Session
from app.models import Wallet, User
from app.schemas import WalletResponse
import logging

logger = logging.getLogger(__name__)


class WalletService:
    """Service for wallet management operations"""
    
    @staticmethod
    def get_wallet(db: Session, user_id: int) -> Wallet:
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
    def get_balance(db: Session, user_id: int) -> float:
        """
        Get current wallet balance
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Balance amount or None
        """
        wallet = WalletService.get_wallet(db, user_id)
        return wallet.balance if wallet else None
    
    @staticmethod
    def deduct_balance(db: Session, user_id: int, amount: float) -> bool:
        """
        Deduct amount from wallet
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to deduct
            
        Returns:
            True if successful, False if insufficient balance
        """
        wallet = WalletService.get_wallet(db, user_id)
        if not wallet:
            raise ValueError(f"Wallet not found for user {user_id}")
        
        if wallet.balance < amount:
            return False
        
        wallet.balance -= amount
        db.commit()
        logger.info(f"✓ Balance deducted: {user_id}, Amount: {amount}")
        return True
    
    @staticmethod
    def add_balance(db: Session, user_id: int, amount: float) -> bool:
        """
        Add amount to wallet
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to add
            
        Returns:
            True if successful
        """
        wallet = WalletService.get_wallet(db, user_id)
        if not wallet:
            raise ValueError(f"Wallet not found for user {user_id}")
        
        wallet.balance += amount
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
