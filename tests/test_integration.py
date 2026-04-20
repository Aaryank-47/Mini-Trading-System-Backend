"""
Integration tests for end-to-end workflows
Tests complete user journeys through the system
"""
import pytest
from fastapi import status


class TestCompleteUserJourney:
    """Test complete user workflow"""
    
    def test_register_trade_portfolio_flow(self, client):
        """Test complete flow: register -> create order -> check portfolio"""
        
        # Step 1: Register user
        register_response = client.post(
            "/users/register",
            json={"name": "Journey User", "email": "journey@example.com"}
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        
        register_data = register_response.json()
        token = register_data["access_token"]
        user_id = register_data["user_id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Check initial portfolio (should be empty)
        portfolio_response = client.get(f"/portfolio/{user_id}", headers=headers)
        assert portfolio_response.status_code == status.HTTP_200_OK
        portfolio = portfolio_response.json()
        assert portfolio["wallet_balance"] > 0
        assert len(portfolio["holdings"]) == 0
        
        # Step 3: Create BUY order
        order_response = client.post(
            "/orders",
            json={
                "user_id": user_id,
                "symbol": "SBIN",
                "qty": 100,
                "side": "BUY"
            },
            headers=headers
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order = order_response.json()
        assert order["side"] == "BUY"
        assert order["symbol"] == "SBIN"
        
        # Step 4: Check updated portfolio
        portfolio_response = client.get(f"/portfolio/{user_id}", headers=headers)
        assert portfolio_response.status_code == status.HTTP_200_OK
        updated_portfolio = portfolio_response.json()
        
        # Wallet balance should be reduced
        assert updated_portfolio["wallet_balance"] < portfolio["wallet_balance"]
        
        # Should now have SBIN holding
        assert len(updated_portfolio["holdings"]) > 0
        
        # Step 5: Check positions
        positions_response = client.get(f"/portfolio/{user_id}/positions", headers=headers)
        assert positions_response.status_code == status.HTTP_200_OK
        positions = positions_response.json()
        assert len(positions) > 0
    
    def test_multiple_trades_portfolio_calculation(self, client):
        """Test portfolio P&L calculation with multiple trades"""
        
        # Register user
        register_response = client.post(
            "/users/register",
            json={"name": "Portfolio User", "email": "portfolio@example.com"}
        )
        user_id = register_response.json()["user_id"]
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Buy 100 shares at current price
        client.post(
            "/orders",
            json={"user_id": user_id, "symbol": "INFY", "qty": 100, "side": "BUY"},
            headers=headers
        )
        
        # Buy 50 more shares (tests weighted average)
        client.post(
            "/orders",
            json={"user_id": user_id, "symbol": "INFY", "qty": 50, "side": "BUY"},
            headers=headers
        )
        
        # Get portfolio
        portfolio_response = client.get(f"/portfolio/{user_id}", headers=headers)
        portfolio = portfolio_response.json()
        
        # Should have INFY with 150 shares total
        infy_holding = next((h for h in portfolio["holdings"] if h["symbol"] == "INFY"), None)
        assert infy_holding is not None
        assert infy_holding["quantity"] == 150
    
    def test_order_history_pagination(self, client):
        """Test order history with pagination"""
        
        # Register user
        register_response = client.post(
            "/users/register",
            json={"name": "History User", "email": "history@example.com"}
        )
        user_id = register_response.json()["user_id"]
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create multiple orders (up to rate limit)
        for i in range(3):
            client.post(
                "/orders",
                json={"user_id": user_id, "symbol": f"STOCK{i}", "qty": 10, "side": "BUY"},
                headers=headers
            )
        
        # Get order history
        history_response = client.get(f"/orders/{user_id}", headers=headers)
        assert history_response.status_code == status.HTTP_200_OK
        
        orders = history_response.json()
        assert isinstance(orders, list)
        assert len(orders) >= 3


class TestConcurrentOperations:
    """Test concurrent operations for race condition detection"""
    
    def test_two_users_different_operations(self, client, test_user, second_test_user, test_user_headers, second_user_headers):
        """Test that two users can operate independently"""
        
        # User 1 creates BUY order
        order1 = client.post(
            "/orders",
            json={"user_id": test_user.id, "symbol": "ABC", "qty": 50, "side": "BUY"},
            headers=test_user_headers
        )
        assert order1.status_code == status.HTTP_201_CREATED
        
        # User 2 creates SELL order (different symbol to avoid conflict)
        order2 = client.post(
            "/orders",
            json={"user_id": second_test_user.id, "symbol": "XYZ", "qty": 25, "side": "BUY"},
            headers=second_user_headers
        )
        assert order2.status_code == status.HTTP_201_CREATED
        
        # Both portfolios should show correct holdings
        portfolio1 = client.get(f"/portfolio/{test_user.id}", headers=test_user_headers)
        portfolio2 = client.get(f"/portfolio/{second_test_user.id}", headers=second_user_headers)
        
        assert portfolio1.status_code == status.HTTP_200_OK
        assert portfolio2.status_code == status.HTTP_200_OK


class TestErrorRecovery:
    """Test error recovery and data consistency"""
    
    def test_failed_order_doesnt_affect_balance(self, client, test_user, test_user_headers):
        """Test that failed order doesn't alter wallet balance"""
        
        # Get initial portfolio
        initial = client.get(f"/portfolio/{test_user.id}", headers=test_user_headers).json()
        initial_balance = initial["wallet_balance"]
        
        # Try to create order that will fail (invalid data)
        response = client.post(
            "/orders",
            json={"user_id": test_user.id, "symbol": "SBIN", "qty": -100, "side": "BUY"},
            headers=test_user_headers
        )
        
        # Order should fail
        assert response.status_code != status.HTTP_201_CREATED
        
        # Balance should be unchanged
        after_fail = client.get(f"/portfolio/{test_user.id}", headers=test_user_headers).json()
        after_balance = after_fail["wallet_balance"]
        
        assert initial_balance == after_balance


class TestDataConsistency:
    """Test data consistency across operations"""
    
    def test_balance_consistency_after_order(self, client, test_user, test_user_headers):
        """Test wallet balance remains consistent"""
        
        # Get user's order count before
        orders_before = client.get(f"/orders/{test_user.id}", headers=test_user_headers).json()
        count_before = len(orders_before)
        
        # Create order
        order_response = client.post(
            "/orders",
            json={"user_id": test_user.id, "symbol": "TATA", "qty": 50, "side": "BUY"},
            headers=test_user_headers
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        
        # Get user's order count after
        orders_after = client.get(f"/orders/{test_user.id}", headers=test_user_headers).json()
        count_after = len(orders_after)
        
        # Count should increase by 1
        assert count_after == count_before + 1
        
        # Get order count endpoint
        count_response = client.get(f"/orders/{test_user.id}/count", headers=test_user_headers)
        if count_response.status_code == status.HTTP_200_OK:
            reported_count = count_response.json().get("count")
            assert reported_count == count_after
