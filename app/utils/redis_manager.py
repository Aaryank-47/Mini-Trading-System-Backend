"""
Redis utility module for managing real-time price storage
"""
import redis
from redis import Redis
from app.config import get_settings
from typing import Optional
import json

settings = get_settings()

# Global Redis client instance
redis_client: Optional[Redis] = None


def init_redis() -> Redis:
    """Initialize and return Redis client"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        # Test connection
        try:
            redis_client.ping()
            print("✓ Connected to Redis successfully!")
        except Exception as e:
            print(f"✗ Failed to connect to Redis: {e}")
            raise
    return redis_client


def get_redis_client() -> Redis:
    """Get Redis client instance"""
    global redis_client
    if redis_client is None:
        return init_redis()
    return redis_client


def set_price(symbol: str, price: float) -> None:
    """Set price for a symbol in Redis"""
    client = get_redis_client()
    key = f"price:{symbol}"
    client.set(key, price)


def get_price(symbol: str) -> Optional[float]:
    """Get current price for a symbol from Redis"""
    client = get_redis_client()
    key = f"price:{symbol}"
    price = client.get(key)
    if price is not None:
        try:
            return float(price)
        except ValueError:
            return None
    return None


def get_all_prices(symbols: list) -> dict:
    """Get prices for multiple symbols"""
    client = get_redis_client()
    prices = {}
    for symbol in symbols:
        price = get_price(symbol)
        if price is not None:
            prices[symbol] = price
    return prices


def clear_prices() -> None:
    """Clear all prices from Redis"""
    client = get_redis_client()
    keys = client.keys("price:*")
    if keys:
        client.delete(*keys)


def health_check() -> bool:
    """Check Redis connection health"""
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception:
        return False
