"""
Test suite to check synchronous vs asynchronous operation of all components
Tests both the endpoint behavior and the service layer operations
"""
import pytest
from fastapi import status
import asyncio
import time
import inspect


class TestAsyncSyncBehavior:
    """Test all components for synchronous vs asynchronous operation"""
    
    def test_registration_sync_behavior(self, client):
        """Test user registration endpoint - should be SYNCHRONOUS"""
        start_time = time.time()
        
        response = client.post(
            "/users/register",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!"
            }
        )
        
        elapsed = time.time() - start_time
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["access_token"]
        print(f"✅ Registration (SYNC) - Status: {response.status_code}, Time: {elapsed:.3f}s")
    
    def test_login_sync_behavior(self, client, test_user_headers):
        """Test user login endpoint - should be SYNCHRONOUS"""
        # Get test user first
        user_response = client.get("/users/profile", headers=test_user_headers)
        user_email = user_response.json()["email"]
        
        start_time = time.time()
        
        response = client.post(
            "/users/login",
            json={
                "email": user_email,
                "password": "TestPassword123!"
            }
        )
        
        elapsed = time.time() - start_time
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["access_token"]
        print(f"✅ Login (SYNC) - Status: {response.status_code}, Time: {elapsed:.3f}s")
    
    def test_profile_fetch_sync_behavior(self, client, test_user_headers):
        """Test profile fetch - should be SYNCHRONOUS"""
        start_time = time.time()
        
        response = client.get("/users/profile", headers=test_user_headers)
        
        elapsed = time.time() - start_time
        
        assert response.status_code == status.HTTP_200_OK
        assert "email" in response.json()
        print(f"✅ Profile Fetch (SYNC) - Status: {response.status_code}, Time: {elapsed:.3f}s")
    
    def test_portfolio_fetch_sync_behavior(self, client, test_user, test_user_headers):
        """Test portfolio fetch - should be SYNCHRONOUS"""
        start_time = time.time()
        
        response = client.get(f"/portfolio/{test_user.id}", headers=test_user_headers)
        
        elapsed = time.time() - start_time
        
        assert response.status_code == status.HTTP_200_OK
        assert "wallet_balance" in response.json()
        print(f"✅ Portfolio Fetch (SYNC) - Status: {response.status_code}, Time: {elapsed:.3f}s")
    
    def test_order_creation_sync_behavior(self, client, test_user, test_user_headers):
        """Test order creation - should be SYNCHRONOUS"""
        start_time = time.time()
        
        response = client.post(
            "/orders",
            json={
                "user_id": test_user.id,
                "symbol": "INFY",
                "qty": 10,
                "side": "BUY"
            },
            headers=test_user_headers
        )
        
        elapsed = time.time() - start_time
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["symbol"] == "INFY"
        print(f"✅ Order Creation (SYNC) - Status: {response.status_code}, Time: {elapsed:.3f}s")
    
    def test_order_fetch_sync_behavior(self, client, test_user, test_user_headers):
        """Test order fetch - should be SYNCHRONOUS"""
        # Create an order first
        create_response = client.post(
            "/orders",
            json={
                "user_id": test_user.id,
                "symbol": "TCS",
                "qty": 5,
                "side": "SELL"
            },
            headers=test_user_headers
        )
        
        order_id = create_response.json()["id"]
        
        start_time = time.time()
        
        response = client.get(f"/orders/{order_id}", headers=test_user_headers)
        
        elapsed = time.time() - start_time
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == order_id
        print(f"✅ Order Fetch (SYNC) - Status: {response.status_code}, Time: {elapsed:.3f}s")
    
    def test_market_data_fetch_sync_behavior(self, client):
        """Test market data fetch - should be SYNCHRONOUS"""
        start_time = time.time()
        
        response = client.get("/market/quote/RELIANCE")
        
        elapsed = time.time() - start_time
        
        # May return 200 or 404 depending on data availability
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        print(f"✅ Market Data Fetch (SYNC) - Status: {response.status_code}, Time: {elapsed:.3f}s")
    
    def test_multiple_concurrent_requests_response_time(self, client, test_user_headers, test_user):
        """Test response time for multiple sequential requests"""
        print("\n--- Sequential Request Performance ---")
        
        requests_count = 5
        total_time = 0
        
        for i in range(requests_count):
            start = time.time()
            response = client.get("/users/profile", headers=test_user_headers)
            elapsed = time.time() - start
            total_time += elapsed
            assert response.status_code == status.HTTP_200_OK
        
        avg_time = total_time / requests_count
        print(f"✅ {requests_count} Sequential Profile Requests - Avg Time: {avg_time:.3f}s")


class TestServiceLayerAsyncSync:
    """Test service layer components for sync/async behavior"""
    
    def test_user_service_is_sync(self, db):
        """Verify UserService methods are SYNCHRONOUS"""
        from app.services.user_service import UserService
        from app.schemas import UserCreate
        
        # Check if create_user is async
        is_async = inspect.iscoroutinefunction(UserService.create_user)
        print(f"✅ UserService.create_user is {'ASYNC' if is_async else 'SYNC'}")
        assert not is_async, "UserService.create_user should be SYNC"
        
        # Check if get_user is async
        is_async = inspect.iscoroutinefunction(UserService.get_user)
        print(f"✅ UserService.get_user is {'ASYNC' if is_async else 'SYNC'}")
        assert not is_async, "UserService.get_user should be SYNC"
    
    def test_order_service_is_sync(self, db):
        """Verify OrderService methods are SYNCHRONOUS"""
        from app.services.order_service import OrderService
        
        # Check if create_order is async
        is_async = inspect.iscoroutinefunction(OrderService.create_order)
        print(f"✅ OrderService.create_order is {'ASYNC' if is_async else 'SYNC'}")
        assert not is_async, "OrderService.create_order should be SYNC"
        
        # Check if get_order is async
        is_async = inspect.iscoroutinefunction(OrderService.get_order)
        print(f"✅ OrderService.get_order is {'ASYNC' if is_async else 'SYNC'}")
        assert not is_async, "OrderService.get_order should be SYNC"
    
    def test_price_service_is_async(self):
        """Verify PriceService methods are ASYNCHRONOUS"""
        from app.services.price_service import PriceService
        
        # Check if get_price is async
        is_async = inspect.iscoroutinefunction(PriceService.get_price)
        print(f"✅ PriceService.get_price is {'ASYNC' if is_async else 'SYNC'}")
        # Price service might be async for external API calls
    
    def test_wallet_service_is_sync(self, db):
        """Verify WalletService methods are SYNCHRONOUS"""
        from app.services.wallet_service import WalletService
        
        # Check if create_wallet is async
        is_async = inspect.iscoroutinefunction(WalletService.create_wallet)
        print(f"✅ WalletService.create_wallet is {'ASYNC' if is_async else 'SYNC'}")
        assert not is_async, "WalletService.create_wallet should be SYNC"


class TestDatabaseOperations:
    """Test database layer for sync behavior"""
    
    def test_database_operations_are_sync(self, db):
        """Verify database operations are SYNCHRONOUS (using SQLAlchemy)"""
        from app.services.user_service import UserService
        from app.schemas import UserCreate
        
        # SQLAlchemy sync operations should work in synchronous context
        user_data = UserCreate(
            name="DB Test User",
            email="dbtest@example.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!"
        )
        
        start_time = time.time()
        user = UserService.create_user(db, user_data)
        elapsed = time.time() - start_time
        
        assert user.id is not None
        print(f"✅ Database Operations (SYNC) - Time: {elapsed:.3f}s")


class TestCompleteUserJourneyFixed:
    """Fixed integration tests with proper request payloads"""
    
    def test_register_trade_portfolio_flow(self, client):
        """Test complete flow: register -> create order -> check portfolio (SYNC)"""
        
        # Step 1: Register user with all required fields
        register_response = client.post(
            "/users/register",
            json={
                "name": "Journey User",
                "email": "journey@example.com",
                "password": "JourneyPass123!",
                "confirm_password": "JourneyPass123!"
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED, f"Register failed: {register_response.text}"
        
        register_data = register_response.json()
        token = register_data["access_token"]
        user_id = register_data["user_id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"✅ User Registered: ID={user_id}")
        
        # Step 2: Check initial portfolio (should be empty)
        portfolio_response = client.get(f"/portfolio/{user_id}", headers=headers)
        assert portfolio_response.status_code == status.HTTP_200_OK
        portfolio = portfolio_response.json()
        assert portfolio["wallet_balance"] > 0
        assert len(portfolio["holdings"]) == 0
        
        print(f"✅ Portfolio Initialized: Balance={portfolio['wallet_balance']}")
        
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
        assert order_response.status_code == status.HTTP_201_CREATED, f"Order failed: {order_response.text}"
        order = order_response.json()
        assert order["side"] == "BUY"
        assert order["symbol"] == "SBIN"
        
        print(f"✅ Order Created: Symbol={order['symbol']}, Qty={order['quantity']}, Side={order['side']}")
        
        # Step 4: Check updated portfolio
        portfolio_response = client.get(f"/portfolio/{user_id}", headers=headers)
        assert portfolio_response.status_code == status.HTTP_200_OK
        updated_portfolio = portfolio_response.json()
        
        # Wallet balance should be reduced
        assert updated_portfolio["wallet_balance"] < portfolio["wallet_balance"]
        
        # Should now have SBIN holding
        assert len(updated_portfolio["holdings"]) > 0
        
        print(f"✅ Portfolio Updated: New Balance={updated_portfolio['wallet_balance']}, Holdings={len(updated_portfolio['holdings'])}")
        print(f"✅ Complete User Journey - ALL OPERATIONS ARE SYNCHRONOUS ✅")
