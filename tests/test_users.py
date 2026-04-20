"""
Unit tests for User API endpoints
Tests registration, authentication, and profile access
"""
import pytest
from fastapi import status
from app.schemas import UserCreate


class TestUserRegistration:
    """Test user registration endpoint"""
    
    def test_register_user_success(self, client):
        """Test successful user registration"""
        response = client.post(
            "/users/register",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "password": "JohnPass123!",
                "confirm_password": "JohnPass123!"
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user_id" in data
    
    def test_register_user_duplicate_email(self, client, test_user):
        """Test registration with duplicate email fails"""
        response = client.post(
            "/users/register",
            json={
                "name": "Another User",
                "email": test_user.email,
                "password": "AnotherPass123!",
                "confirm_password": "AnotherPass123!"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_user_invalid_email(self, client):
        """Test registration with invalid email"""
        response = client.post(
            "/users/register",
            json={
                "name": "John Doe",
                "email": "invalid-email",
                "password": "JohnPass123!",
                "confirm_password": "JohnPass123!"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_user_empty_name(self, client):
        """Test registration with empty name"""
        response = client.post(
            "/users/register",
            json={
                "name": "",
                "email": "john@example.com",
                "password": "JohnPass123!",
                "confirm_password": "JohnPass123!"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_user_xss_in_name(self, client):
        """Test registration with XSS attempt in name"""
        response = client.post(
            "/users/register",
            json={
                "name": "<script>alert('xss')</script>",
                "email": "john@example.com",
                "password": "JohnPass123!",
                "confirm_password": "JohnPass123!"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserProfile:
    """Test user profile endpoint"""
    
    def test_get_profile_authenticated(self, client, test_user, test_user_headers):
        """Test getting own profile"""
        response = client.get("/users/profile", headers=test_user_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
    
    def test_get_profile_unauthenticated(self, client):
        """Test getting profile without authentication"""
        response = client.get("/users/profile")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_profile_invalid_token(self, client):
        """Test getting profile with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/users/profile", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRateLimiting:
    """Test rate limiting on registration"""
    
    def test_rate_limit_registration(self, client):
        """Test rate limiting on user registration (5/minute)"""
        # Make 5 successful requests
        for i in range(5):
            response = client.post(
                "/users/register",
                json={
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "password": f"Pass{i}123!",
                    "confirm_password": f"Pass{i}123!"
                }
            )
            assert response.status_code == status.HTTP_201_CREATED
        
        # 6th request should be rate limited
        response = client.post(
            "/users/register",
            json={
                "name": "User 6",
                "email": "user6@example.com",
                "password": "Pass6123!",
                "confirm_password": "Pass6123!"
            }
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestUserLogin:
    """Test user login endpoint"""
    
    def test_login_success(self, client, test_user):
        """Test successful user login"""
        response = client.post(
            "/users/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123!"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == test_user.id
        assert data["expires_in"] == 1800  # 30 minutes in seconds
    
    def test_login_invalid_email(self, client):
        """Test login with non-existent email"""
        response = client.post(
            "/users/login",
            json={
                "email": "nonexistent@example.com",
                "password": "TestPassword123!"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_invalid_password(self, client, test_user):
        """Test login with incorrect password"""
        response = client.post(
            "/users/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_missing_email(self, client):
        """Test login with missing email"""
        response = client.post(
            "/users/login",
            json={"password": "TestPassword123!"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_missing_password(self, client, test_user):
        """Test login with missing password"""
        response = client.post(
            "/users/login",
            json={"email": test_user.email}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestTokenRefresh:
    """Test token refresh endpoint"""
    
    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh"""
        # First, login to get tokens
        login_response = client.post(
            "/users/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123!"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]
        
        # Now refresh the access token
        response = client.post(
            "/users/token/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == test_user.id
        assert data["expires_in"] == 1800
    
    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token"""
        response = client.post(
            "/users/token/refresh",
            json={"refresh_token": "invalid-token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token_missing(self, client):
        """Test refresh with missing refresh_token"""
        response = client.post(
            "/users/token/refresh",
            json={}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_refresh_token_access_token_as_refresh(self, client, test_user, test_user_token):
        """Test using access token as refresh token (should fail)"""
        response = client.post(
            "/users/token/refresh",
            json={"refresh_token": test_user_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
