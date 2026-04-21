"""
Redis utility module with automatic reconnection and error handling
Handles real-time price storage with graceful degradation on connection loss
"""
import redis
from redis import Redis, ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError
from app.config import get_settings
from typing import Optional
import json
import logging
import time
import threading
import ssl

logger = logging.getLogger(__name__)
settings = get_settings()

# ============= REDIS CONNECTION MANAGER =============
class RedisConnectionManager:
    """Manages Redis connection with automatic reconnection and health checks"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[Redis] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2  # seconds (with exponential backoff)
        self.health_check_interval = 30  # seconds
        self.connection_timeout = 5  # seconds
        self.health_check_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self._reconnect_log_cooldown = 10  # seconds
        self._last_reconnect_log_time = 0.0
        self._reconnect_cooldown_after_max = 30  # seconds
        self._next_reconnect_allowed_at = 0.0
        self._last_max_attempt_log_time = 0.0
    
    def connect(self) -> bool:
        """Establish Redis connection with error handling"""
        with self.lock:
            try:
                use_ssl = self.redis_url.startswith("rediss://")
                logger.info(f"🔄 Connecting to Redis (SSL={use_ssl}): {self.redis_url}")

                pool_kwargs = {
                    "decode_responses": True,
                    "socket_connect_timeout": self.connection_timeout,
                    "socket_keepalive": True,
                    "socket_keepalive_options": {
                        1: 1,  # TCP_KEEPIDLE
                        2: 1,  # TCP_KEEPINTVL
                        3: 1   # TCP_KEEPCNT
                    }
                }

                if use_ssl:
                    # redis-py 5 with rediss:// should use SSLConnection (do not pass ssl=).
                    # Upstash commonly works with CERT_NONE in hosted/serverless environments.
                    pool_kwargs["connection_class"] = redis.SSLConnection
                    pool_kwargs["ssl_cert_reqs"] = ssl.CERT_NONE

                pool = ConnectionPool.from_url(self.redis_url, **pool_kwargs)
                client = Redis(connection_pool=pool)

                try:
                    client.ping()
                except Exception as ping_error:
                    self.is_connected = False
                    self.client = None
                    logger.warning(f"⚠️  Redis ping failed after client init: {ping_error}")
                    return False

                self.client = client
                self.is_connected = True
                self.reconnect_attempts = 0
                self._next_reconnect_allowed_at = 0.0
                logger.info(f"✅ Connected to Redis successfully (SSL={use_ssl})")
                return True
                
            except (ConnectionError, TimeoutError) as e:
                self.is_connected = False
                self.client = None
                logger.warning(f"⚠️  Redis connection failed: {e}")
                return False
            except Exception as e:
                self.is_connected = False
                self.client = None
                logger.error(f"❌ Unexpected Redis error: {e}")
                return False
    
    def reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff"""
        now = time.time()

        # After max retries, pause reconnect attempts for a cooldown window.
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            if now < self._next_reconnect_allowed_at:
                if now - self._last_max_attempt_log_time >= self._reconnect_log_cooldown:
                    wait_seconds = int(self._next_reconnect_allowed_at - now)
                    logger.warning(
                        f"⚠️  Redis reconnect cooldown active, next retry in {wait_seconds}s"
                    )
                    self._last_max_attempt_log_time = now
                return False

            # Cooldown elapsed: reset attempts and start a new retry window.
            self.reconnect_attempts = 0

        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"❌ Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            return False
        
        # Exponential backoff: 2s, 4s, 8s, 16s, 32s
        delay = self.reconnect_delay * (2 ** self.reconnect_attempts)
        self.reconnect_attempts += 1
        
        logger.info(f"⏳ Waiting {delay}s before reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        time.sleep(delay)

        connected = self.connect()
        if not connected and self.reconnect_attempts >= self.max_reconnect_attempts:
            self._next_reconnect_allowed_at = time.time() + self._reconnect_cooldown_after_max
            logger.error(
                f"❌ Max reconnection attempts ({self.max_reconnect_attempts}) reached; "
                f"cooling down for {self._reconnect_cooldown_after_max}s"
            )
        return connected
    
    def get_client(self) -> Optional[Redis]:
        """Get Redis client with reconnection attempt if needed"""
        # If connected, use existing client
        if self.is_connected and self.client:
            return self.client
        
        # If not connected, try to reconnect
        now = time.time()
        if now - self._last_reconnect_log_time >= self._reconnect_log_cooldown:
            logger.warning("⚠️  Redis client disconnected, attempting to reconnect...")
            self._last_reconnect_log_time = now
        if self.reconnect():
            return self.client

        return None
    
    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy"""
        try:
            if not self.is_connected or not self.client:
                return False
            
            self.client.ping()
            return True
        except Exception as e:
            logger.warning(f"⚠️  Redis health check failed: {e}")
            self.is_connected = False
            return False
    
    def start_health_check(self):
        """Start background health check thread"""
        if self.health_check_thread and self.health_check_thread.is_alive():
            logger.info("Health check thread already running")
            return
        
        logger.info("🩺 Starting Redis health check thread...")
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()
    
    def _health_check_loop(self):
        """Background health check loop"""
        while True:
            try:
                time.sleep(self.health_check_interval)
                
                if not self.is_healthy():
                    logger.warning("⚠️  Redis health check failed, attempting reconnect...")
                    if not self.reconnect():
                        logger.error("❌ Failed to reconnect after health check")
                else:
                    logger.debug("✅ Redis health check passed")
                    
            except Exception as e:
                logger.error(f"❌ Health check thread error: {e}")
                time.sleep(self.health_check_interval)
    
    def close(self):
        """Close Redis connection"""
        try:
            if self.client:
                self.client.close()
                logger.info("✓ Redis connection closed")
        except Exception as e:
            logger.warning(f"⚠️  Error closing Redis connection: {e}")
        finally:
            self.is_connected = False
            self.client = None


# Global connection manager instance
redis_manager: Optional[RedisConnectionManager] = None
_unavailable_price_log_timestamps = {}
_unavailable_price_log_cooldown = 30  # seconds


# ============= PUBLIC API =============
def init_redis() -> Optional[Redis]:
    """Initialize and return Redis client"""
    global redis_manager
    if redis_manager is None:
        redis_manager = RedisConnectionManager(settings.redis_url)
        redis_manager.connect()
        redis_manager.start_health_check()
    return redis_manager.get_client()


def get_redis_client() -> Optional[Redis]:
    """Get Redis client instance with auto-reconnect"""
    global redis_manager
    if redis_manager is None:
        return init_redis()
    return redis_manager.get_client()


def reconnect_redis() -> bool:
    """Manually trigger Redis reconnection"""
    global redis_manager
    if redis_manager is None:
        return init_redis() is not None
    return redis_manager.reconnect()


def set_price(symbol: str, price: float) -> bool:
    """Set price for a symbol in Redis with error handling"""
    try:
        client = get_redis_client()
        if not client:
            now = time.time()
            last_logged = _unavailable_price_log_timestamps.get(symbol, 0.0)
            if now - last_logged >= _unavailable_price_log_cooldown:
                logger.warning(f"⚠️  Cannot set price for {symbol}: Redis unavailable")
                _unavailable_price_log_timestamps[symbol] = now
            return False
        
        key = f"price:{symbol}"
        client.set(key, price)
        return True
    except (ConnectionError, TimeoutError) as e:
        logger.warning(f"⚠️  Redis connection error setting {symbol}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error setting price for {symbol}: {e}")
        return False


def get_price(symbol: str) -> Optional[float]:
    """Get current price for a symbol from Redis with fallback"""
    try:
        client = get_redis_client()
        if not client:
            logger.debug(f"⚠️  Redis unavailable for {symbol}")
            return None
        
        key = f"price:{symbol}"
        price = client.get(key)
        if price is not None:
            try:
                return float(price)
            except ValueError:
                return None
        return None
    except (ConnectionError, TimeoutError) as e:
        logger.warning(f"⚠️  Redis connection error getting {symbol}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error getting price for {symbol}: {e}")
        return None


def get_all_prices(symbols: list) -> dict:
    """Get prices for multiple symbols with partial fallback"""
    prices = {}
    try:
        client = get_redis_client()
        if not client:
            logger.debug("⚠️  Redis unavailable for bulk price fetch")
            return prices
        
        for symbol in symbols:
            try:
                price = get_price(symbol)
                if price is not None:
                    prices[symbol] = price
            except Exception as e:
                logger.warning(f"⚠️  Error fetching {symbol}: {e}")
                continue
        
        return prices
    except Exception as e:
        logger.error(f"❌ Error in bulk price fetch: {e}")
        return prices


def clear_prices() -> bool:
    """Clear all prices from Redis with error handling"""
    try:
        client = get_redis_client()
        if not client:
            logger.warning("⚠️  Cannot clear prices: Redis unavailable")
            return False
        
        keys = client.keys("price:*")
        if keys:
            client.delete(*keys)
        return True
    except (ConnectionError, TimeoutError) as e:
        logger.warning(f"⚠️  Redis connection error clearing prices: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error clearing prices: {e}")
        return False


def health_check() -> dict:
    """Check Redis connection health and return status"""
    global redis_manager
    if redis_manager is None:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": "Redis manager not initialized"
        }
    
    is_healthy = redis_manager.is_healthy()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "connected": redis_manager.is_connected,
        "attempts": redis_manager.reconnect_attempts,
        "max_attempts": redis_manager.max_reconnect_attempts
    }


def get_connection_status() -> str:
    """Get human-readable connection status"""
    status = health_check()
    
    # Handle uninitialized state
    if "error" in status:
        return "⏳ Initializing..."
    
    if status.get("connected", False):
        return "✅ Connected"
    
    attempts = status.get("attempts", 0)
    max_attempts = status.get("max_attempts", 5)
    
    if attempts < max_attempts:
        return f"⏳ Reconnecting ({attempts}/{max_attempts})"
    else:
        return "❌ Disconnected (max attempts reached)"


def close_redis():
    """Close Redis connection gracefully"""
    global redis_manager
    if redis_manager:
        redis_manager.close()
