"""
Unit tests for the Trading Execution Engine
"""
import pytest
from fastapi import status
from decimal import Decimal
from app.models import Order, OrderStatus
from app.services.trading_engine import TradingEngine
from app.services.order_service import OrderService

class TestTradingEngine:
    
    def test_limit_buy_order_pending_and_execute(self, client, test_user, test_user_headers, db):
        """Test that a LIMIT BUY stays pending until price drops, then executes."""
        # 1. Create LIMIT BUY order for 10 shares @ 600
        order_data = {
            "user_id": test_user.id,
            "symbol": "SBIN",
            "qty": 10,
            "side": "BUY",
            "order_type": "LIMIT",
            "limit_price": 600.00
        }
        
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["order_type"] == "LIMIT"
        assert data["status"] == "PENDING"
        order_id = data["id"]
        
        # 2. Simulate price update where price is still too high (650)
        TradingEngine.evaluate_pending_orders(db, "SBIN", current_price=650.00)
        
        # Check status is still PENDING
        db.expire_all()
        order = OrderService.get_order(db, order_id)
        assert order.status == OrderStatus.PENDING
        
        # 3. Simulate price update where price drops to limit (600)
        TradingEngine.evaluate_pending_orders(db, "SBIN", current_price=600.00)
        
        # Check status is now COMPLETED
        db.expire_all()
        order = OrderService.get_order(db, order_id)
        assert order.status == OrderStatus.COMPLETED
        assert order.price is not None
        assert float(order.price) == 600.00
        
    def test_stop_loss_sell_order(self, client, test_user, test_user_headers, db):
        """Test that a STOP LOSS SELL stays pending until price drops below stop, then executes."""
        # First, buy some shares so we have a position to sell
        buy_data = {
            "user_id": test_user.id,
            "symbol": "RELIANCE",
            "qty": 20,
            "side": "BUY",
            "order_type": "MARKET"
        }
        
        response = client.post("/orders", json=buy_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_201_CREATED
        
        # 1. Create STOP LOSS SELL order for 10 shares @ 900
        order_data = {
            "user_id": test_user.id,
            "symbol": "RELIANCE",
            "qty": 10,
            "side": "SELL",
            "order_type": "STOP_LOSS",
            "stop_price": 900.00
        }
        
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "PENDING"
        order_id = data["id"]
        
        # 2. Simulate price drops to 950 (still above stop loss)
        TradingEngine.evaluate_pending_orders(db, "RELIANCE", current_price=950.00)
        
        db.expire_all()
        order = OrderService.get_order(db, order_id)
        assert order.status == OrderStatus.PENDING
        
        # 3. Simulate price drops to 890 (below stop loss trigger)
        TradingEngine.evaluate_pending_orders(db, "RELIANCE", current_price=890.00)
        
        db.expire_all()
        order = OrderService.get_order(db, order_id)
        assert order.status == OrderStatus.COMPLETED
        assert order.price is not None
        assert float(order.price) == 890.00

    def test_cancel_pending_order(self, client, test_user, test_user_headers, db):
        # Create LIMIT BUY
        order_data = {
            "user_id": test_user.id,
            "symbol": "TCS",
            "qty": 5,
            "side": "BUY",
            "order_type": "LIMIT",
            "limit_price": 3000.00
        }
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        order_id = response.json()["id"]
        
        # Cancel the order
        cancel_response = client.delete(f"/orders/{order_id}", headers=test_user_headers)
        assert cancel_response.status_code == status.HTTP_200_OK
        
        # Verify status is CANCELLED
        db.expire_all()
        order = OrderService.get_order(db, order_id)
        assert order.status == OrderStatus.CANCELLED
        
        # Verify it doesn't execute when price drops
        TradingEngine.evaluate_pending_orders(db, "TCS", current_price=2900.00)
        db.expire_all()
        order = OrderService.get_order(db, order_id)
        assert order.status == OrderStatus.CANCELLED

    def test_duplicate_execution_prevention(self, client, test_user, test_user_headers, db):
        """Test that a pending order won't execute twice."""
        order_data = {
            "user_id": test_user.id,
            "symbol": "TATA",
            "qty": 10,
            "side": "BUY",
            "order_type": "LIMIT",
            "limit_price": 400.00
        }
        
        response = client.post("/orders", json=order_data, headers=test_user_headers)
        order_id = response.json()["id"]
        
        # Simulate execution
        TradingEngine.evaluate_pending_orders(db, "TATA", current_price=390.00)
        db.expire_all()
        order = OrderService.get_order(db, order_id)
        assert order.status == OrderStatus.COMPLETED
        
        # Attempt execution again directly via order service
        executed_order = OrderService.execute_pending_order(db, order_id, Decimal("380.00"))
        
        # The execute_pending_order should return the already completed order without changing it
        assert executed_order.status == OrderStatus.COMPLETED
        # The price should still be 390
        db.expire_all()
        final_order = OrderService.get_order(db, order_id)
        assert final_order is not None
        assert final_order.price is not None
        assert float(final_order.price) == 390.00  # type: ignore
