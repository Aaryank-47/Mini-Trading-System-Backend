"""
Password hashing and verification utilities
Handles secure password storage and validation
"""
from passlib.context import CryptContext
from typing import Optional
import re

# Configure bcrypt context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt
    
    Args:
        password: Plain text password to hash
    
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its hash
    
    Args:
        plain_password: Plain text password from user
        hashed_password: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> Optional[str]:
    """
    Validate password meets minimum security requirements
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password: Password to validate
    
    Returns:
        None if valid, error message if invalid
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};:',.<>?/\\|`~]", password):
        return "Password must contain at least one special character"
    
    return None
