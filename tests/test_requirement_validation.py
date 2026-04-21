"""
Requirement-focused tests for market pricing, order execution, and positions.

These tests avoid external Redis dependency by mocking Redis calls,
then validate the business rules requested in the task statement.
"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.main import update_prices_background
from app.models import OrderStatus, Position
from app.schemas import OrderCreate
from app.services.order_service import OrderService
from app.utils import redis_manager


class FakeRedisClient:
    """Minimal in-memory Redis client used for key-level behavior tests."""

    def __init__(self):
        self.store = {}

    def set(self, key, value):
        self.store[key] = str(value)

    def get(self, key):
        return self.store.get(key)


class TestMarketPriceSystem:
    def test_redis_key_format_and_fetch(self, monkeypatch):
        """Prices are stored as price:{SYMBOL} and fetched from Redis values."""
        fake_client = FakeRedisClient()
        monkeypatch.setattr(redis_manager, "get_redis_client", lambda: fake_client)

        assert redis_manager.set_price("SBIN", 820.50) is True
        assert redis_manager.set_price("RELIANCE", 2950.00) is True

        assert fake_client.get("price:SBIN") == "820.5"
        assert fake_client.get("price:RELIANCE") == "2950.0"
        assert redis_manager.get_price("SBIN") == 820.5
        assert redis_manager.get_price("RELIANCE") == 2950.0

    @pytest.mark.asyncio
    async def test_background_updates_prices_and_broadcasts(self, monkeypatch):
        """Background task updates every loop and broadcasts price_update events."""
        from app import main as main_module

        sleep_calls = {"count": 0}

        async def fake_sleep(_seconds):
            sleep_calls["count"] += 1
            if sleep_calls["count"] >= 2:
                raise asyncio.CancelledError()

        import asyncio

        monkeypatch.setattr(main_module.asyncio, "sleep", fake_sleep)
        monkeypatch.setattr(
            main_module.PriceService,
            "update_prices",
            lambda: {"SBIN": 820.5, "RELIANCE": 2950.0},
        )

        broadcast_mock = AsyncMock()
        monkeypatch.setattr(main_module.connection_manager, "broadcast_to_all", broadcast_mock)

        await update_prices_background()

        assert sleep_calls["count"] >= 1
        assert broadcast_mock.await_count >= 2


class TestOrderExecutionAndPositions:
    def test_buy_order_executes_immediately_with_redis_price(self, db, test_user, monkeypatch):
        """BUY uses Redis price, deducts wallet, creates COMPLETED order and position."""
        monkeypatch.setattr("app.services.order_service.get_price", lambda symbol: 820.50)

        initial_balance = Decimal(test_user.wallet.balance)

        order = OrderService.execute_order(
            db,
            OrderCreate(user_id=test_user.id, symbol="SBIN", qty=10, side="BUY"),
        )

        db.refresh(test_user.wallet)
        position = db.query(Position).filter(Position.user_id == test_user.id, Position.symbol == "SBIN").first()

        assert order.status == OrderStatus.COMPLETED
        assert order.price == Decimal("820.50")
        assert order.total_amount == Decimal("8205.00")
        assert Decimal(test_user.wallet.balance) == initial_balance - Decimal("8205.00")
        assert position is not None
        assert position.quantity == 10
        assert position.average_price == Decimal("820.50")

    def test_sell_order_checks_position_and_credits_wallet(self, db, test_user, monkeypatch):
        """SELL validates quantity, reduces position, and adds proceeds to wallet."""
        prices = iter([100.0, 120.0])
        monkeypatch.setattr("app.services.order_service.get_price", lambda symbol: next(prices))

        start_balance = Decimal(test_user.wallet.balance)

        buy_order = OrderService.execute_order(
            db,
            OrderCreate(user_id=test_user.id, symbol="SBIN", qty=10, side="BUY"),
        )
        sell_order = OrderService.execute_order(
            db,
            OrderCreate(user_id=test_user.id, symbol="SBIN", qty=4, side="SELL"),
        )

        db.refresh(test_user.wallet)
        position = db.query(Position).filter(Position.user_id == test_user.id, Position.symbol == "SBIN").first()

        assert buy_order.status == OrderStatus.COMPLETED
        assert sell_order.status == OrderStatus.COMPLETED
        assert position is not None
        assert position.quantity == 6
        assert position.average_price == Decimal("100.00")

        expected_balance = start_balance - Decimal("1000.00") + Decimal("480.00")
        assert Decimal(test_user.wallet.balance) == expected_balance

    def test_sell_fails_when_insufficient_position(self, db, test_user, monkeypatch):
        """SELL should fail when user does not hold enough quantity."""
        monkeypatch.setattr("app.services.order_service.get_price", lambda symbol: 500.0)

        # Build a small position first.
        OrderService.execute_order(
            db,
            OrderCreate(user_id=test_user.id, symbol="SBIN", qty=2, side="BUY"),
        )

        with pytest.raises(ValueError, match="Insufficient quantity"):
            OrderService.execute_order(
                db,
                OrderCreate(user_id=test_user.id, symbol="SBIN", qty=10, side="SELL"),
            )


