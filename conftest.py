"""
Pytest configuration and fixtures for the Trading Platform Backend
"""
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set test database URL BEFORE importing anything from app
os.environ['DATABASE_URL'] = "sqlite:///:memory:"
os.environ['REDIS_URL'] = "redis://localhost:6379"  
os.environ['SECRET_KEY'] = "test-secret-key-for-testing-only"
os.environ['DEBUG'] = "False"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
# Clear any cached settings
get_settings.cache_clear()

# Reload database module with new settings
if 'app.database' in sys.modules:
    del sys.modules['app.database']

from app.database import Base, get_db
from app.main import app
from app.security import create_access_token
from app.services.user_service import UserService
from app.schemas import UserCreate
from decimal import Decimal

# Create test database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables in test database
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for tests"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db():
    """Database session fixture"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine) 


@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client fixture"""
    app.dependency_overrides[get_db] = override_get_db
    with patch("app.core.lifespan.init_db", return_value=None), \
         patch("app.core.lifespan.init_redis", return_value=None), \
         patch("app.core.lifespan.close_redis", return_value=None), \
         patch("app.core.lifespan.publish_realtime_event", return_value=False), \
         patch("app.core.lifespan.PriceService.initialize_prices", return_value=None), \
         patch("app.core.lifespan.asyncio.create_task") as create_task_mock:
        # Create a mock task using a custom class that doesn't require a running event loop at instantiation
        class MockAwaitableTask:
            def __await__(self):
                if False:
                    yield
            def cancel(self):
                pass
        task_mock = MockAwaitableTask()
        create_task_mock.return_value = task_mock
        with TestClient(app) as test_client:
            yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db):
    """Create a test user"""
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password="TestPassword123!",
        confirm_password="TestPassword123!"
    )
    user = UserService.create_user(db, user_data)
    return user


@pytest.fixture(scope="function")
def test_user_token(test_user):
    """Create JWT token for test user"""
    return create_access_token(test_user.id)


@pytest.fixture(scope="function")
def test_user_headers(test_user_token):
    """Authorization headers with JWT token"""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture(scope="function")
def second_test_user(db):
    """Create a second test user"""
    user_data = UserCreate(
        name="Second User",
        email="second@example.com",
        password="SecondPass123!",
        confirm_password="SecondPass123!"
    )
    user = UserService.create_user(db, user_data)
    return user


@pytest.fixture(scope="function")
def second_user_token(second_test_user):
    """Create JWT token for second user"""
    return create_access_token(second_test_user.id)


@pytest.fixture(scope="function")
def second_user_headers(second_user_token):
    """Authorization headers for second user"""
    return {"Authorization": f"Bearer {second_user_token}"}


# Test data
@pytest.fixture(scope="function")
def valid_order_data():
    """Valid order creation data"""
    return {
        "user_id": 1,
        "symbol": "SBIN",
        "qty": 100,
        "side": "BUY"
    }


@pytest.fixture(scope="function")
def invalid_order_data():
    """Invalid order data for negative testing"""
    return [
        {"user_id": 1, "symbol": "SBIN", "qty": -100, "side": "BUY"},  # Negative qty
        {"user_id": 1, "symbol": "SBIN", "qty": 0, "side": "BUY"},  # Zero qty
        {"user_id": 1, "symbol": "sbin", "qty": 100, "side": "BUY"},  # Lowercase symbol
        {"user_id": 1, "symbol": "SB1N", "qty": 100, "side": "BUY"},  # Symbol with number
        {"user_id": 1, "symbol": "SBIN", "qty": 100, "side": "INVALID"},  # Invalid side
        {"user_id": 1, "symbol": "SBIN", "qty": 2000000, "side": "BUY"},  # Qty > 1M
    ]


@pytest.fixture(scope="function")
def empty_market_prices():
    """Empty market prices payload for no-data scenarios."""
    return {}


@pytest.fixture(scope="function")
def large_market_prices():
    """Generate deterministic large market data set (1000 symbols)."""
    return {f"SYM{i:04d}": float(100 + i) for i in range(1000)}


@pytest.fixture(scope="function")
def websocket_clients_100():
    """Create 100 websocket mocks for stress broadcasting tests."""
    clients = []
    for _ in range(100):
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        clients.append(ws)
    return clients


@pytest.fixture(scope="function", autouse=True)
def mock_redis_prices():
    """Globally mock Redis get_price and get_all_prices to avoid running Redis dependencies"""
    prices = {
        "SBIN": 820.50,
        "RELIANCE": 2950.00,
        "INFY": 1600.00,
        "TCS": 3800.00,
        "TATA": 400.00,
        "ABC": 150.00,
    }

    def get_price_mock(symbol):
        return prices.get(symbol.upper(), 100.0)

    def get_all_prices_mock(symbols=None):
        if not symbols:
            return prices
        return {sym: get_price_mock(sym) for sym in symbols}

    with patch("app.utils.redis_manager.get_price", side_effect=get_price_mock), \
         patch("app.utils.redis_manager.get_all_prices", side_effect=get_all_prices_mock), \
         patch("app.services.order_service.get_price", side_effect=get_price_mock), \
         patch("app.services.price_service.get_price", side_effect=get_price_mock), \
         patch("app.services.price_service.get_all_prices", side_effect=get_all_prices_mock), \
         patch("app.core.lifespan.publish_realtime_event", return_value=False), \
         patch("app.routers.portfolio.get_price", side_effect=get_price_mock):
        yield


@pytest.fixture(scope="function", autouse=True)
def reset_rate_limiter():
    """Reset the slowapi rate limiter state between tests to avoid carrying over hits"""
    if hasattr(app.state, "limiter") and hasattr(app.state.limiter, "_storage"):
        app.state.limiter._storage.reset()

