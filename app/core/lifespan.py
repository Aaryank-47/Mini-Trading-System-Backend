"""Application lifespan and background task management."""
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
import logging

from fastapi import FastAPI

from app.config import get_settings
from app.database import init_db
from app.services.price_service import PriceService
from app.utils.redis_manager import close_redis, init_redis
from app.websocket import PRICE_UPDATES_CHANNEL, connection_manager, publish_realtime_event, start_realtime_bridge, stop_realtime_bridge

logger = logging.getLogger(__name__)
settings = get_settings()
price_update_task = None


async def update_prices_background() -> None:
    """Update market prices and broadcast changes to connected WebSocket clients."""
    logger.info("Price update task running")

    while True:
        try:
            await asyncio.sleep(1)
            updated_prices = PriceService.update_prices()

            if updated_prices:
                for symbol, price in updated_prices.items():
                    payload = {
                        "symbol": symbol,
                        "symbol_name": PriceService.get_symbol_name(symbol),
                        "price": price,
                    }
                    published = await asyncio.to_thread(
                        publish_realtime_event,
                        PRICE_UPDATES_CHANNEL,
                        "price_update",
                        payload,
                    )
                    if not published:
                        await connection_manager.broadcast({
                            "event": "price_update",
                            "data": payload,
                            "timestamp": datetime.now().isoformat(),
                        })
        except asyncio.CancelledError:
            logger.info("Price update task cancelled")
            break
        except Exception as exc:
            logger.error(f"Error updating prices: {exc}")
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle with graceful degradation."""
    logger.info("=" * 60)
    logger.info("Starting Trading Platform API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug: {settings.debug}")
    logger.info("=" * 60)

    startup_success = True

    try:
        logger.info("Attempting database initialization")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.error(f"Database initialization failed: {exc}")
        startup_success = False

    try:
        logger.info("Attempting Redis initialization")
        init_redis()
        logger.info("Redis initialized successfully")
    except Exception as exc:
        logger.warning(f"Redis initialization failed: {exc}")
        logger.warning("Continuing without Redis cache")

    try:
        logger.info("Initializing market prices")
        PriceService.initialize_prices()
        logger.info("Market prices initialized")
    except Exception as exc:
        logger.error(f"Price initialization failed: {exc}")

    global price_update_task
    try:
        logger.info("Starting background price update task")
        price_update_task = asyncio.create_task(update_prices_background())
        logger.info("Background price update task started")
    except Exception as exc:
        logger.error(f"Failed to start price update task: {exc}")

    try:
        await connection_manager.start_heartbeat()
        start_realtime_bridge(connection_manager)
    except Exception as exc:
        logger.warning(f"WebSocket realtime bridge could not start: {exc}")

    if startup_success:
        logger.info("Application startup completed successfully")
    else:
        logger.warning("Application started with errors")

    yield

    logger.info("Shutting down Trading Platform API")

    try:
        close_redis()
        logger.info("Redis connection closed")
    except Exception as exc:
        logger.warning(f"Error closing Redis: {exc}")

    if price_update_task:
        price_update_task.cancel()
        try:
            await price_update_task
        except asyncio.CancelledError:
            pass
        logger.info("Price update task stopped")

    try:
        await stop_realtime_bridge()
        await connection_manager.stop_heartbeat()
    except Exception as exc:
        logger.warning(f"Error stopping WebSocket realtime tasks: {exc}")

    logger.info("Application shutdown completed")
