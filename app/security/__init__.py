"""
JWT Authentication and Authorization module
Handles token creation, validation, and user authentication
"""
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, Tuple
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.config import get_settings
from app.utils.password import hash_password, verify_password
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
bearer_scheme = HTTPBearer()

# Constants
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token for a user
    
    Args:
        user_id: The user ID to encode in the token
        expires_delta: Optional expiration time (defaults to settings.access_token_expire_minutes)
    
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": TOKEN_TYPE_ACCESS
    }
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        logger.info(f"✓ Access token created for user {user_id}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise


def create_refresh_token(user_id: int) -> str:
    """
    Create a JWT refresh token for a user
    
    Args:
        user_id: The user ID to encode in the token
    
    Returns:
        Encoded JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": TOKEN_TYPE_REFRESH
    }
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        logger.info(f"✓ Refresh token created for user {user_id}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create refresh token: {e}")
        raise


def create_token_pair(user_id: int) -> Tuple[str, str]:
    """
    Create both access and refresh tokens for a user
    
    Args:
        user_id: The user ID to create tokens for
    
    Returns:
        Tuple of (access_token, refresh_token)
    """
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return access_token, refresh_token


def verify_token(token: str, token_type: str = TOKEN_TYPE_ACCESS) -> Dict:
    """
    Verify and decode a JWT token
    
    Args:
        token: The JWT token to verify
        token_type: Type of token to verify (access or refresh)
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}"
            )
        
        return payload
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )


async def get_current_user(credentials: Any = Depends(bearer_scheme)) -> int:
    """
    Extract and validate JWT access token from Authorization header
    
    Args:
        credentials: HTTP Bearer token from request header
    
    Returns:
        User ID from the token
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        # Verify it's an access token
        if payload.get("type") != TOKEN_TYPE_ACCESS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("JWT token has no user ID (sub claim)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        return int(user_id)
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


def verify_user_ownership(user_id: int, current_user_id: int) -> None:
    """
    Verify that the current user is accessing their own data
    
    Args:
        user_id: The user ID being accessed
        current_user_id: The authenticated user's ID
    
    Raises:
        HTTPException: If user is not authorized to access this resource
    """
    if user_id != current_user_id:
        logger.warning(f"User {current_user_id} attempted to access user {user_id} resources")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )
