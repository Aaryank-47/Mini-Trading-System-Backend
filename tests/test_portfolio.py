"""
Unit tests for Portfolio and Market API endpoints
Tests portfolio retrieval and market data access
"""
import pytest
from fastapi import status


class TestPortfolioAccess:
    """Test portfolio endpoint access"""
    
    def test_get_portfolio_authenticated(self, client, test_user, test_user_headers):
        """Test getting own portfolio"""
        response = client.get(f"/portfolio/{test_user.id}", headers=test_user_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == test_user.id
        assert "wallet_balance" in data
        assert "holdings" in data
        assert "total_portfolio_value" in data
    
    def test_get_portfolio_unauthenticated(self, client, test_user):
        """Test getting portfolio without authentication"""
        response = client.get(f"/portfolio/{test_user.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_user_cannot_access_other_portfolio(self, client, test_user, second_user_headers):
        """Test that user cannot access another user's portfolio"""
        response = client.get(f"/portfolio/{test_user.id}", headers=second_user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_portfolio_nonexistent_user(self, client, test_user_headers):
        """Test getting portfolio for non-existent user"""
        response = client.get("/portfolio/999", headers=test_user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN  # Ownership check fails


class TestPositions:
    """Test positions endpoint"""
    
    def test_get_positions(self, client, test_user, test_user_headers):
        """Test getting user positions"""
        response = client.get(f"/portfolio/{test_user.id}/positions", headers=test_user_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestMarketData:
    """Test market data endpoints (public)"""
    
    def test_get_market_prices(self, client):
        """Test getting market prices (no auth required)"""
        response = client.get("/market/prices")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_single_price(self, client):
        """Test getting single symbol price"""
        response = client.get("/market/price/SBIN")
        assert response.status_code == status.HTTP_200_OK
        assert "price" in response.json()
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
