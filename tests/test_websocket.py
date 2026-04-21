"""WebSocket tests for connection auth, broadcast behavior, and load scenarios."""
import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

from app.schemas import OrderExecutedMessage, PriceUpdateMessage
from app.websocket import ConnectionManager


class TestWebSocketConnection:
    """Test WebSocket connection establishment and authentication."""

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_endpoint_accepts_valid_user_and_optional_token(self, test_user, test_user_token):
        """Endpoint should connect and disconnect cleanly for valid user/token."""
        from app import main as main_module

        websocket = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=["ping", Exception("disconnect")])

        with patch.object(main_module.UserService, "get_user", return_value=test_user), \
             patch.object(main_module.connection_manager, "connect", new_callable=AsyncMock) as connect_mock, \
             patch.object(main_module.connection_manager, "disconnect", new_callable=AsyncMock) as disconnect_mock:
            await main_module.websocket_endpoint(
                user_id=test_user.id,
                websocket=websocket,
                token=test_user_token,
                db=object(),
            )

        connect_mock.assert_awaited_once()
        disconnect_mock.assert_awaited_once()
        websocket.close.assert_not_called()

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_endpoint_rejects_invalid_token(self, test_user):
        """Invalid token should close websocket with policy violation."""
        from app import main as main_module

        websocket = AsyncMock()

        with patch.object(main_module.UserService, "get_user", return_value=test_user), \
             patch.object(main_module.connection_manager, "connect", new_callable=AsyncMock) as connect_mock:
            await main_module.websocket_endpoint(
                user_id=test_user.id,
                websocket=websocket,
                token="invalid.token",
                db=object(),
            )

        websocket.close.assert_awaited_once()
        assert websocket.close.await_args.kwargs["code"] == status.WS_1008_POLICY_VIOLATION
        connect_mock.assert_not_called()

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_endpoint_rejects_token_user_mismatch(self, test_user, second_user_token):
        """Token user and path user mismatch should be rejected."""
        from app import main as main_module

        websocket = AsyncMock()

        with patch.object(main_module.UserService, "get_user", return_value=test_user), \
             patch.object(main_module.connection_manager, "connect", new_callable=AsyncMock) as connect_mock:
            await main_module.websocket_endpoint(
                user_id=test_user.id,
                websocket=websocket,
                token=second_user_token,
                db=object(),
            )

        websocket.close.assert_awaited_once()
        assert websocket.close.await_args.kwargs["reason"] == "Token mismatch"
        connect_mock.assert_not_called()

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_endpoint_rejects_unknown_user(self):
        """Unknown user should be rejected before websocket accept."""
        from app import main as main_module

        websocket = AsyncMock()

        with patch.object(main_module.UserService, "get_user", return_value=None), \
             patch.object(main_module.connection_manager, "connect", new_callable=AsyncMock) as connect_mock:
            await main_module.websocket_endpoint(
                user_id=999999,
                websocket=websocket,
                token=None,
                db=object(),
            )

        websocket.close.assert_awaited_once()
        assert websocket.close.await_args.kwargs["reason"] == "User not found"
        connect_mock.assert_not_called()


class TestWebSocketMessages:
    """Test message handling from client side."""

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_endpoint_receives_text_message(self, test_user):
        """Endpoint should consume incoming text message and keep loop alive."""
        from app import main as main_module

        websocket = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=["hello-server", Exception("disconnect")])

        with patch.object(main_module.UserService, "get_user", return_value=test_user), \
             patch.object(main_module.connection_manager, "connect", new_callable=AsyncMock), \
             patch.object(main_module.connection_manager, "disconnect", new_callable=AsyncMock):
            await main_module.websocket_endpoint(
                user_id=test_user.id,
                websocket=websocket,
                token=None,
                db=object(),
            )

        assert websocket.receive_text.await_count == 2

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_endpoint_handles_receive_error_and_disconnects(self, test_user):
        """Receive errors should trigger managed disconnect path."""
        from app import main as main_module

        websocket = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=Exception("network error"))

        with patch.object(main_module.UserService, "get_user", return_value=test_user), \
             patch.object(main_module.connection_manager, "connect", new_callable=AsyncMock), \
             patch.object(main_module.connection_manager, "disconnect", new_callable=AsyncMock) as disconnect_mock:
            await main_module.websocket_endpoint(
                user_id=test_user.id,
                websocket=websocket,
                token=None,
                db=object(),
            )

        disconnect_mock.assert_awaited_once()


class TestConnectionManager:
    """Test ConnectionManager functionality."""
    
    @pytest.mark.asyncio
    async def test_connection_manager_connect(self):
        """Test adding a connection to manager"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        user_id = 1
        await manager.connect(user_id, mock_ws)
        
        assert user_id in manager.active_connections
        assert mock_ws in manager.active_connections[user_id]
        mock_ws.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_manager_disconnect(self):
        """Test removing a connection from manager"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        user_id = 1
        await manager.connect(user_id, mock_ws)
        assert user_id in manager.active_connections
        
        await manager.disconnect(user_id, mock_ws)
        assert user_id not in manager.active_connections
    
    @pytest.mark.asyncio
    async def test_connection_manager_broadcast_to_user(self):
        """Test broadcasting message to specific user"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        user_id = 1
        await manager.connect(user_id, mock_ws1)
        await manager.connect(user_id, mock_ws2)
        
        message = {"type": "price_update", "symbol": "AAPL", "price": 150.25}
        await manager.broadcast_to_user(user_id, message)
        
        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_connection_manager_broadcast_to_all(self):
        """Test broadcasting message to all connected users"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws3 = AsyncMock()
        
        await manager.connect(1, mock_ws1)
        await manager.connect(2, mock_ws2)
        await manager.connect(3, mock_ws3)
        
        message = {"type": "system", "text": "Market closed"}
        await manager.broadcast_to_all(message)
        
        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)
        mock_ws3.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_connection_manager_get_active_users(self):
        """Test getting list of active users"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        await manager.connect(1, mock_ws1)
        await manager.connect(2, mock_ws2)
        
        active_users = manager.get_active_users()
        assert set(active_users) == {1, 2}
    
    @pytest.mark.asyncio
    async def test_connection_manager_get_connection_count(self):
        """Test getting connection count for a user"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        user_id = 1
        await manager.connect(user_id, mock_ws1)
        assert manager.get_connection_count(user_id) == 1
        
        await manager.connect(user_id, mock_ws2)
        assert manager.get_connection_count(user_id) == 2
    
    @pytest.mark.asyncio
    async def test_connection_manager_multiple_users_multiple_connections(self):
        """Test manager handles multiple users with multiple connections each"""
        manager = ConnectionManager()
        
        connections = {}
        for user_id in range(1, 4):
            connections[user_id] = []
            for i in range(2):
                mock_ws = AsyncMock()
                await manager.connect(user_id, mock_ws)
                connections[user_id].append(mock_ws)
        
        # Verify all users connected
        assert len(manager.get_active_users()) == 3
        
        # Verify each user has correct connection count
        for user_id in range(1, 4):
            assert manager.get_connection_count(user_id) == 2
    
    @pytest.mark.asyncio
    async def test_connection_manager_handles_send_errors(self):
        """Send failures should not block healthy sockets."""
        manager = ConnectionManager()
        
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        mock_ws1.send_json.side_effect = Exception("Connection lost")
        
        user_id = 1
        await manager.connect(user_id, mock_ws1)
        await manager.connect(user_id, mock_ws2)
        
        message = {"type": "test"}
        await manager.broadcast_to_user(user_id, message)
        
        assert manager.get_connection_count(user_id) == 1
        mock_ws2.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_connection_manager_cleanup_empty_user_set(self):
        """Test manager cleans up empty user connection sets"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        user_id = 1
        await manager.connect(user_id, mock_ws)
        assert user_id in manager.active_connections
        
        await manager.disconnect(user_id, mock_ws)
        assert user_id not in manager.active_connections


class TestWebSocketIntegration:
    """Integration tests for WebSocket with FastAPI route."""

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_multiple_users_endpoint_calls_are_isolated(self, test_user, second_test_user):
        """Separate endpoint calls for separate users should remain isolated."""
        from app import main as main_module

        ws1 = AsyncMock()
        ws1.receive_text = AsyncMock(side_effect=Exception("disconnect"))
        ws2 = AsyncMock()
        ws2.receive_text = AsyncMock(side_effect=Exception("disconnect"))

        def fake_get_user(_, user_id):
            if user_id == test_user.id:
                return test_user
            if user_id == second_test_user.id:
                return second_test_user
            return None

        with patch.object(main_module.UserService, "get_user", side_effect=fake_get_user), \
             patch.object(main_module.connection_manager, "connect", new_callable=AsyncMock) as connect_mock, \
             patch.object(main_module.connection_manager, "disconnect", new_callable=AsyncMock) as disconnect_mock:
            await main_module.websocket_endpoint(test_user.id, ws1, None, object())
            await main_module.websocket_endpoint(second_test_user.id, ws2, None, object())

        assert connect_mock.await_count == 2
        assert disconnect_mock.await_count == 2


class TestWebSocketGlobalManager:
    """Test global connection manager access."""
    
    @pytest.mark.asyncio
    async def test_global_connection_manager_instance(self):
        """Test global connection manager is accessible"""
        from app.websocket import get_connection_manager
        
        manager = get_connection_manager()
        assert isinstance(manager, ConnectionManager)
    
    @pytest.mark.asyncio
    async def test_global_connection_manager_persistence(self):
        """Test global connection manager maintains state"""
        from app.websocket import connection_manager as global_manager
        
        mock_ws = AsyncMock()
        await global_manager.connect(999, mock_ws)
        
        count = global_manager.get_connection_count(999)
        assert count == 1
        
        await global_manager.disconnect(999, mock_ws)


class TestWebSocketRobustness:
    """Test robustness and error handling around message delivery."""

    @pytest.mark.asyncio
    async def test_broadcast_removes_only_failing_socket(self):
        """One failing socket must not prevent delivery to healthy sockets."""
        manager = ConnectionManager()
        user_id = 1

        broken_ws = AsyncMock()
        healthy_ws = AsyncMock()
        broken_ws.send_json.side_effect = Exception("write failed")

        await manager.connect(user_id, broken_ws)
        await manager.connect(user_id, healthy_ws)

        payload = {"event": "price_update", "symbol": "SBIN", "price": 500.25}
        await manager.broadcast_to_user(user_id, payload)

        assert manager.get_connection_count(user_id) == 1
        healthy_ws.send_json.assert_called_once_with(payload)
    
    @pytest.mark.asyncio
    async def test_connection_manager_handles_none_user_id(self):
        """Test manager handles None user_id gracefully"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        count = manager.get_connection_count(None)
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_user(self):
        """Test broadcasting to user with no connections"""
        manager = ConnectionManager()
        
        message = {"type": "test"}
        await manager.broadcast_to_user(9999, message)
    
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self):
        """Test disconnecting non-existent connection doesn't error"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        await manager.disconnect(9999, mock_ws)


class TestWebSocketConcurrency:
    """Test WebSocket concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connects_same_user(self):
        """Test multiple concurrent connections from same user"""
        manager = ConnectionManager()
        user_id = 1
        
        mocks = [AsyncMock() for _ in range(5)]
        for mock_ws in mocks:
            await manager.connect(user_id, mock_ws)
        
        assert manager.get_connection_count(user_id) == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_broadcasts(self):
        """Test concurrent broadcast operations"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        await manager.connect(1, mock_ws1)
        await manager.connect(2, mock_ws2)
        
        messages = [
            {"type": "update", "id": 1},
            {"type": "update", "id": 2},
            {"type": "update", "id": 3}
        ]
        
        for msg in messages:
            await manager.broadcast_to_all(msg)
        
        assert mock_ws1.send_json.call_count == 3
        assert mock_ws2.send_json.call_count == 3


class TestWebSocketNoDataHandling:
    """Validate behavior when market data is empty or missing."""

    @pytest.mark.asyncio
    async def test_background_update_with_no_prices_does_not_broadcast(self):
        """No market prices means no broadcasts should be emitted in that cycle."""
        from app import main as main_module

        with patch.object(main_module.PriceService, "update_prices", return_value={}), \
             patch.object(main_module.connection_manager, "broadcast_to_all", new_callable=AsyncMock) as broadcast_mock, \
             patch("app.main.asyncio.sleep", new=AsyncMock(side_effect=[None, asyncio.CancelledError])):
            await main_module.update_prices_background()

        broadcast_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_background_update_broadcasts_each_symbol(self, large_market_prices):
        """Non-empty price updates should broadcast one message per symbol."""
        from app import main as main_module

        sample_prices = dict(list(large_market_prices.items())[:20])
        with patch.object(main_module.PriceService, "update_prices", return_value=sample_prices), \
             patch.object(main_module.connection_manager, "broadcast_to_all", new_callable=AsyncMock) as broadcast_mock, \
             patch("app.main.asyncio.sleep", new=AsyncMock(side_effect=[None, asyncio.CancelledError])):
            await main_module.update_prices_background()

        assert broadcast_mock.await_count == len(sample_prices)
        first_payload = broadcast_mock.await_args_list[0].args[0]
        assert first_payload["event"] == "price_update"
        assert "symbol" in first_payload
        assert "price" in first_payload
        assert "timestamp" in first_payload


class TestWebSocketHighLoad:
    """Stress behavior with large symbol set and concurrent clients."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    @pytest.mark.performance
    @pytest.mark.stress
    async def test_broadcast_high_volume_prices_to_100_clients(
        self,
        large_market_prices,
        websocket_clients_100,
    ):
        """Broadcast 1000 symbol updates to 100 clients and verify delivery counts."""
        manager = ConnectionManager()

        for idx, ws in enumerate(websocket_clients_100, start=1):
            await manager.connect(idx, ws)

        for symbol, price in large_market_prices.items():
            message = {
                "event": "price_update",
                "symbol": symbol,
                "price": price,
                "timestamp": datetime.now().isoformat(),
            }
            await manager.broadcast_to_all(message)

        expected_messages_per_client = len(large_market_prices)
        for ws in websocket_clients_100:
            assert ws.send_json.await_count == expected_messages_per_client


class TestWebSocketSchemas:
    """Test WebSocket message schemas."""
    
    def test_order_executed_message_schema(self):
        """Test OrderExecutedMessage schema validation"""
        message_data = {
            "event": "order_executed",
            "symbol": "AAPL",
            "qty": 10,
            "price": Decimal("150.25"),
            "side": "BUY",
            "status": "filled",
            "total_amount": Decimal("1502.50"),
            "timestamp": datetime.now()
        }
        
        msg = OrderExecutedMessage(**message_data)
        assert msg.symbol == "AAPL"
        assert msg.qty == 10
        assert msg.side == "BUY"
        assert msg.status == "filled"
    
    def test_price_update_message_schema(self):
        """Test PriceUpdateMessage schema validation"""
        message_data = {
            "event": "price_update",
            "symbol": "AAPL",
            "price": Decimal("155.50"),
            "timestamp": datetime.now()
        }
        
        msg = PriceUpdateMessage(**message_data)
        assert msg.symbol == "AAPL"
        assert msg.price == Decimal("155.50")
        assert msg.event == "price_update"
