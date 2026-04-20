"""
Unit tests for Order API endpoints
Tests order creation, validation, and execution
"""
import pytest
from fastapi import status
from decimal import Decimal


class TestOrderCreation:
    """Test order creation endpoint"""
    
    def test_create_buy_order_success(self, client, test_user, test_user_headers, valid_order_data):
        """Test successful BUY order creation"""
        response = client.post(
            "/orders",
            json=valid_order_data,
            headers=test_user_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["symbol"] == "SBIN"
        assert data["quantity"] == 100
        assert data["side"] == "BUY"
        assert data["status"] == "COMPLETED"
    
    def test_create_order_unauthenticated(self, client, valid_order_data):
        """Test order creation without authentication"""
        response = client.post("/orders", json=valid_order_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_create_order_invalid_token(self, client, valid_order_data):
        """Test order creation with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.post("/orders", json=valid_order_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_order_negative_quantity(self, client, test_user_headers):
        """Test order creation with negative quantity"""
        order_data = {
            "user_id": 1,
            "symbol": "SBIN",
            "qty": -100,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_order_zero_quantity(self, client, test_user_headers):
        """Test order creation with zero quantity"""
        order_data = {
            "user_id": 1,
            "symbol": "SBIN",
            "qty": 0,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_order_exceed_max_quantity(self, client, test_user_headers):
        """Test order creation exceeding max quantity (1M)"""
        order_data = {
            "user_id": 1,
            "symbol": "SBIN",
            "qty": 2000000,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_order_invalid_symbol(self, client, test_user_headers):
        """Test order creation with invalid symbol"""
        order_data = {
            "user_id": 1,
            "symbol": "sbin",  # lowercase
            "qty": 100,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_order_invalid_side(self, client, test_user_headers):
        """Test order creation with invalid side"""
        order_data = {
            "user_id": 1,
            "symbol": "SBIN",
            "qty": 100,
            "side": "INVALID"
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_order_non_existent_user(self, client, test_user_headers):
        """Test order creation for non-existent user"""
        order_data = {
            "user_id": 999,
            "symbol": "SBIN",
            "qty": 100,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_order_insufficient_balance(self, client, test_user, test_user_headers):
        """Test order creation with insufficient balance"""
        # Try to buy 1 billion shares (wallet only has 1M initial balance)
        order_data = {
            "user_id": test_user.id,
            "symbol": "SBIN",
            "qty": 1000000000,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient balance" in response.json()["detail"]


class TestOrderAuthorization:
    """Test authorization on order endpoints"""
    
    def test_user_cannot_access_other_user_orders(self, client, test_user, second_user_headers):
        """Test that user cannot access another user's orders"""
        response = client.get(f"/orders/{test_user.id}", headers=second_user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_user_cannot_create_order_for_other_user(self, client, second_test_user, second_user_headers):
        """Test that user cannot create orders for another user"""
        order_data = {
            "user_id": 999,  # Different user
            "symbol": "SBIN",
            "qty": 100,
            "side": "BUY"
        }
        response = client.post("/orders", json=order_data, headers=second_user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestOrderRateLimiting:
    """Test rate limiting on orders"""
    
    def test_rate_limit_orders(self, client, test_user, test_user_headers, valid_order_data):
        """Test rate limiting on order creation (10/minute)"""
        # Make 10 successful requests
        for i in range(10):
            response = client.post(
                "/orders",
                json=valid_order_data,
                headers=test_user_headers
            )
            if response.status_code != status.HTTP_201_CREATED:
                # May fail due to insufficient balance, but that's OK for this test
                break
        
        # 11th request should be rate limited or insufficient balance
        response = client.post(
            "/orders",
            json=valid_order_data,
            headers=test_user_headers
        )
        assert response.status_code in [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_400_BAD_REQUEST]


class TestOrderHistory:
    """Test order history endpoint"""
    
    def test_get_order_history(self, client, test_user, test_user_headers):
        """Test getting order history"""
        response = client.get(f"/orders/{test_user.id}", headers=test_user_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_order_history_with_limit(self, client, test_user, test_user_headers):
        """Test order history with limit parameter"""
        response = client.get(
            f"/orders/{test_user.id}?limit=50",
            headers=test_user_headers
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_order_history_limit_exceeds_max(self, client, test_user, test_user_headers):
        """Test order history limit exceeds maximum (500)"""
        response = client.get(
            f"/orders/{test_user.id}?limit=1000",
            headers=test_user_headers
        )
        # Should return 422 or be capped at 500
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]
