"""
User management API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserCreate, UserResponse, TokenResponse, LoginRequest, LoginResponse, AccessTokenResponse
from app.services.user_service import UserService
from app.security import create_access_token, create_token_pair, verify_token, get_current_user, verify_user_ownership, TOKEN_TYPE_REFRESH
from typing import List
from datetime import timedelta
import logging

from app.utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}}
)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register new user and return JWT token
    
    Returns:
    - access_token: JWT token for authentication
    - token_type: "bearer"
    - user_id: New user's ID
    
    Usage:
    ```
    POST /users/register
    Content-Type: application/json
    
    {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    ```
    """
    try:
        user = UserService.create_user(db, user_data)
        token = create_access_token(user.id)
        logger.info(f"✓ User registered: {user.id} ({user_data.email})")
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id
        }
    except ValueError as e:
        logger.warning(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user with email and password
    
    Returns:
    - access_token: JWT access token (30 minutes expiration)
    - refresh_token: JWT refresh token (7 days expiration)
    - token_type: "bearer"
    - user_id: User's ID
    - expires_in: Access token expiration in seconds (1800)
    
    Usage:
    ```
    POST /users/login
    Content-Type: application/json
    
    {
        "email": "john@example.com",
        "password": "SecurePass123!"
    }
    ```
    """
    try:
        user = UserService.authenticate_user(db, login_data.email, login_data.password)
        access_token, refresh_token = create_token_pair(user.id)
        
        logger.info(f"✓ User logged in: {user.id} ({login_data.email})")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "expires_in": 1800
        }
    except ValueError as e:
        logger.warning(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/token/refresh", response_model=AccessTokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
def refresh_token(
    request: Request,
    refresh_request: dict,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Returns:
    - access_token: New JWT access token (30 minutes expiration)
    - token_type: "bearer"
    - user_id: User's ID
    - expires_in: Access token expiration in seconds (1800)
    
    Usage:
    ```
    POST /users/token/refresh
    Content-Type: application/json
    
    {"refresh_token": "<REFRESH_TOKEN>"}
    ```
    """
    try:
        refresh_token_str = refresh_request.get("refresh_token")
        if not refresh_token_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="refresh_token is required"
            )
        payload = verify_token(refresh_token_str, token_type=TOKEN_TYPE_REFRESH)
        user_id = int(payload.get("sub"))
        user = UserService.get_user(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        access_token = create_access_token(user_id)
        
        logger.info(f"✓ Token refreshed for user: {user_id}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "expires_in": 1800
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )



@router.get("/profile", response_model=UserResponse)
def get_profile(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get authenticated user's profile
    
    Requires: Bearer token in Authorization header
    
    Usage:
    ```
    GET /users/profile
    Authorization: Bearer <JWT_TOKEN>
    ```
    """
    user = UserService.get_user(db, current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user details (authenticated users can only access their own profile)
    
    Requires: Bearer token in Authorization header
    """
    verify_user_ownership(user_id, current_user_id)
    
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    return user


@router.get("", response_model=List[UserResponse])
def get_all_users(
    skip: int = 0,
    limit: int = Query(50, le=100),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all users with pagination
    
    Requires: Bearer token in Authorization header
    """
    users = UserService.get_all_users(db, skip=skip, limit=limit)
    return users


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a user (can only delete own account)
    
    Requires: Bearer token in Authorization header
    """
    verify_user_ownership(user_id, current_user_id)
    
    success = UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    logger.info(f"✓ User deleted: {user_id}")
    return None
