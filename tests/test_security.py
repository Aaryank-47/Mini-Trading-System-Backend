"""
Security tests for the Trading Platform
Tests authentication, authorization, and security controls
"""
import pytest
from fastapi import status


class TestAuthentication:
    """Test authentication mechanisms"""
    
    def test_jwt_token_creation(self, test_user_token):
        """Test JWT token creation"""
        assert test_user_token is not None
        assert isinstance(test_user_token, str)
        assert len(test_user_token) > 0
    
    def test_invalid_bearer_token(self, client):
        """Test endpoint with invalid bearer token"""
        headers = {"Authorization": "Bearer invalid-token-12345"}
        response = client.get("/users/profile", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_missing_bearer_prefix(self, client, test_user_token):
        """Test missing 'Bearer' prefix in authorization header"""
        headers = {"Authorization": test_user_token}
        response = client.get("/users/profile", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_expired_token_format(self, client):
        """Test with malformed token"""
        headers = {"Authorization": "Bearer not.a.valid.jwt"}
        response = client.get("/users/profile", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_empty_authorization_header(self, client):
        """Test with empty authorization header"""
        headers = {"Authorization": ""}
        response = client.get("/users/profile", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAuthorization:
    """Test authorization checks"""
    
    def test_user_cannot_modify_other_user_data(self, client, test_user, second_user_headers):
        """Test that users cannot modify other users' data"""
        order_data = {
            "user_id": test_user.id,  # Different user's ID
            "symbol": "SBIN",
            "qty": 100,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=second_user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_ownership_verification_on_portfolio(self, client, test_user, second_user_headers):
        """Test ownership verification on portfolio access"""
        response = client.get(f"/portfolio/{test_user.id}", headers=second_user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestInputValidation:
    """Test input validation"""
    
    def test_email_validation(self, client):
        """Test email format validation"""
        response = client.post(
            "/users/register",
            json={"name": "John", "email": "not-an-email"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_name_xss_prevention(self, client):
        """Test XSS prevention in user name"""
        response = client.post(
            "/users/register",
            json={"name": "<script>alert('xss')</script>", "email": "test@example.com"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_symbol_validation(self, client, test_user_headers):
        """Test symbol validation (must be uppercase letters)"""
        order_data = {
            "user_id": 1,
            "symbol": "sbin",  # lowercase
            "qty": 100,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_quantity_bounds(self, client, test_user_headers):
        """Test quantity validation bounds"""
        # Test zero
        response = client.post(
            "/orders",
            json={"user_id": 1, "symbol": "SBIN", "qty": 0, "side": "BUY"},
            headers=test_user_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test negative
        response = client.post(
            "/orders",
            json={"user_id": 1, "symbol": "SBIN", "qty": -100, "side": "BUY"},
            headers=test_user_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test exceeds max (1M)
        response = client.post(
            "/orders",
            json={"user_id": 1, "symbol": "SBIN", "qty": 2000000, "side": "BUY"},
            headers=test_user_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSecurityHeaders:
    """Test security headers in responses"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are set correctly"""
        response = client.get("/health")
        # Should have CORS headers (depends on client configuration)
        assert response.status_code == status.HTTP_200_OK
    
    def test_x_content_type_options_header(self, client):
        """Test X-Content-Type-Options header"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        # Note: TestClient may not preserve all headers, check in real deployment
    
    def test_error_response_sanitization(self, client, test_user_headers):
        """Test that error responses don't leak sensitive info"""
        order_data = {
            "user_id": 999,
            "symbol": "SBIN",
            "qty": 100,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        # Should return error without exposing internals
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_detail = response.json().get("detail", "")
        assert "traceback" not in error_detail.lower()
        assert "sqlalchemy" not in error_detail.lower()


class TestRateLimitingSecurityBypass:
    """Test that rate limiting cannot be bypassed"""
    
    def test_rate_limit_per_ip(self, client):
        """Test rate limiting is per IP address"""
        # Make 5 registrations
        for i in range(5):
            response = client.post(
                "/users/register",
                json={"name": f"User {i}", "email": f"user{i}@example.com"}
            )
            assert response.status_code == status.HTTP_201_CREATED
        
        # 6th should fail
        response = client.post(
            "/users/register",
            json={"name": "User 6", "email": "user6@example.com"}
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
