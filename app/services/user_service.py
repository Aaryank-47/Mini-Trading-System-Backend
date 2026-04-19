"""
User service for managing user-related operations
"""
from sqlalchemy.orm import Session
from app.models import User, Wallet
from app.schemas import UserCreate, UserResponse
from app.database import Base
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations"""
    
    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """
        Create a new user with default wallet
        
        Args:
            db: Database session
            user_data: User creation data
            
        Returns:
            Created user object
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")
        
        # Create new user
        db_user = User(
            name=user_data.name,
            email=user_data.email
        )
        db.add(db_user)
        db.flush()  # Flush to get user ID
        
        # Auto-create wallet with default balance
        wallet = Wallet(
            user_id=db_user.id,
            balance=1000000.0  # ₹10,00,000
        )
        db.add(wallet)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"✓ User created: {db_user.id} - {db_user.email}")
        return db_user
    
    @staticmethod
    def get_user(db: Session, user_id: int) -> User:
        """
        Get user by ID
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            User object or None
        """
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User:
        """
        Get user by email
        
        Args:
            db: Database session
            email: User email
            
        Returns:
            User object or None
        """
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> list:
        """
        Get all users with pagination
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of users
        """
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """
        Delete user and associated data
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        db.delete(user)
        db.commit()
        logger.info(f"✓ User deleted: {user_id}")
        return True
