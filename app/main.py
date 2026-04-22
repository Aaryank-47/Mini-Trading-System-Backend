"""
Main FastAPI application
Initializes the trading platform API with all routes and background tasks
"""
from fastapi import FastAPI, WebSocket, Depends, status, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime
from jose import jwt, JWTError

from slowapi.errors import RateLimitExceeded
from app.utils.rate_limiter import limiter

from app.config import get_settings
from app.database import init_db, get_db
from app.utils.redis_manager import init_redis, health_check, get_connection_status, reconnect_redis, close_redis
from app.utils.health_check import (
    get_overall_health, 
    get_detailed_health_report, 
    get_quick_status,
    HealthMetrics
)
from app.services.price_service import PriceService
from app.services.user_service import UserService
from app.security import get_current_user
from app.websocket import connection_manager
from app.routers import users, orders, portfolio, market

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

price_update_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    Startup: Initialize database, Redis, and background tasks
    Shutdown: Clean up resources
    
    ⚠️ IMPORTANT: Never raise exceptions in lifespan startup.
    Use graceful degradation instead - app should start even if
    some services are temporarily unavailable.
    """
    # ============= STARTUP =============
    logger.info("="*60)
    logger.info("🚀 Starting Trading Platform API...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug: {settings.debug}")
    logger.info("="*60)
    
    startup_success = True
    
    # Database Initialization (Critical but don't crash)
    try:
        logger.info("📊 Attempting database initialization...")
        init_db()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        logger.error(f"   Make sure MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD are set in environment")
        startup_success = False
        # Don't raise - let app start and retry later if needed
    
    # Redis Initialization (Optional - graceful degradation)
    redis_ok = False
    try:
        logger.info("💾 Attempting Redis initialization...")
        init_redis()
        redis_ok = True
        logger.info("✓ Redis initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Redis initialization failed: {e}")
        logger.warning(f"   Continuing without Redis cache (caching disabled)")
        # Redis is optional, don't crash app
    
    # Price Service Initialization
    try:
        logger.info("📈 Initializing market prices...")
        PriceService.initialize_prices()
        logger.info("✓ Market prices initialized")
    except Exception as e:
        logger.error(f"✗ Price initialization failed: {e}")
        # Price service failure is non-critical
    
    # Background Price Update Task
    global price_update_task
    try:
        logger.info("🔄 Starting background price update task...")
        price_update_task = asyncio.create_task(update_prices_background())
        logger.info("✓ Background price update task started")
    except Exception as e:
        logger.error(f"✗ Failed to start price update task: {e}")
        # Task failure is non-critical
    
    if startup_success:
        logger.info("="*60)
        logger.info("✅ Application startup completed successfully!")
        logger.info("="*60)
    else:
        logger.warning("="*60)
        logger.warning("⚠️  Application started with errors (check logs above)")
        logger.warning("="*60)
    
    yield
    
    # ============= SHUTDOWN =============
    logger.info("🛑 Shutting down Trading Platform API...")
    
    # Close Redis connection
    try:
        close_redis()
        logger.info("✓ Redis connection closed")
    except Exception as e:
        logger.warning(f"⚠️  Error closing Redis: {e}")
    
    # Cancel price update task
    if price_update_task:
        price_update_task.cancel()
        try:
            await price_update_task
        except asyncio.CancelledError:
            pass
        logger.info("✓ Price update task stopped")
    
    logger.info("✅ Application shutdown completed!")



# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A production-ready mini trading platform API",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter

# CORS Configuration
# Dynamically load origins from .env (comma-separated string)
allowed_origins = [
    origin.strip() 
    for origin in settings.allowed_origins.split(",") 
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Relax CSP for development or just use sensible defaults for API
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
    
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track requests and errors for health metrics"""
    try:
        HealthMetrics.increment_requests()
        response = await call_next(request)
        
        # Count errors (5xx responses)
        if response.status_code >= 500:
            HealthMetrics.increment_errors()
        
        return response
    except Exception as e:
        HealthMetrics.increment_errors()
        logger.error(f"Request error: {e}")
        raise


# ============= BACKGROUND TASKS =============
async def update_prices_background():
    """
    Background task that updates market prices every 1 second
    Simulates real-time price fluctuation (±2%)
    """
    logger.info("📈 Price update task running...")
    
    while True:
        try:
            await asyncio.sleep(1)  # Update every 1 second
            
            # Update prices
            updated_prices = PriceService.update_prices()
            
            # Broadcast price updates to all connected WebSocket clients
            if updated_prices:
                for symbol, price in updated_prices.items():
                    message = {
                        "event": "price_update",
                        "symbol": symbol,
                        "price": price,
                        "timestamp": datetime.now().isoformat()
                    }
                    await connection_manager.broadcast_to_all(message)
            
        except asyncio.CancelledError:
            logger.info("📈 Price update task cancelled")
            break
        except Exception as e:
            logger.error(f"Error updating prices: {e}")
            await asyncio.sleep(1)


# ============= HEALTH CHECK ENDPOINTS =============

@app.get("/health")
def health_check_endpoint():
    """
    Basic health check endpoint
    
    Response:
    - status: overall system status (healthy/degraded/unhealthy)
    - uptime: application uptime
    - components: status of database and Redis
    - metrics: server resource usage
    - requests: request statistics
    """
    return get_overall_health()


@app.get("/health/quick")
def health_quick_endpoint():
    """
    Quick health check (minimal response, fast)
    
    Returns: status (ok/warning/error), uptime, component status
    """
    return get_quick_status()


@app.get("/health/detailed")
def health_detailed_endpoint():
    """
    Comprehensive detailed health report
    
    Includes:
    - Component health (database, Redis)
    - Server metrics (CPU, memory, processes)
    - Health checks indicators
    - Application statistics
    """
    return get_detailed_health_report()


@app.get("/health/database")
def health_database_endpoint():
    """Check database connectivity"""
    from app.utils.health_check import check_database_health
    status = check_database_health()
    return {
        "component": "database",
        "status": "✅ Connected" if status["connected"] else "❌ Disconnected",
        "details": status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health/redis")
def health_redis_endpoint():
    """Check Redis connectivity"""
    from app.utils.health_check import check_redis_health
    status = check_redis_health()
    return {
        "component": "redis",
        "status": status["connection_status"],
        "connected": status["connected"],
        "details": status["details"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health/metrics")
def health_metrics_endpoint():
    """Get server metrics (CPU, memory, processes)"""
    from app.utils.health_check import get_server_metrics
    return {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": HealthMetrics.get_uptime_seconds(),
        "uptime_formatted": HealthMetrics.get_uptime_formatted(),
        "requests_total": HealthMetrics.request_count,
        "errors_total": HealthMetrics.error_count,
        "error_rate_percent": round(
            (HealthMetrics.error_count / max(HealthMetrics.request_count, 1)) * 100, 2
        ) if HealthMetrics.request_count > 0 else 0,
        "server_resources": get_server_metrics()
    }


@app.get("/redis/status")
def redis_status_endpoint():
    """Get detailed Redis connection status"""
    status = health_check()
    return {
        "connection_status": get_connection_status(),
        "details": status,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/redis/reconnect")
def redis_reconnect_endpoint():
    """Manually trigger Redis reconnection"""
    logger.info("🔄 Manual Redis reconnection triggered")
    success = reconnect_redis()
    
    return {
        "success": success,
        "status": get_connection_status(),
        "details": health_check(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "description": "A production-ready mini trading platform",
        "docs": "/docs",
        "redoc": "/redoc",
        "health_endpoints": {
            "GET /health": "Overall system health",
            "GET /health/quick": "Quick status check",
            "GET /health/detailed": "Detailed report with metrics",
            "GET /health/database": "Database status only",
            "GET /health/redis": "Redis status only",
            "GET /health/metrics": "Server metrics (CPU, memory)",
            "GET /redis/status": "Redis connection details",
            "POST /redis/reconnect": "Trigger Redis reconnection"
        },
        "status": "running"
    }


# ============= API ROUTES =============
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(portfolio.router)
app.include_router(market.router)


# ============= WEBSOCKET ENDPOINT =============
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    user_id: int,
    websocket: WebSocket,
    token: str = Query(None),  # Optional JWT token for authentication
    db=Depends(get_db)
):
    """
    ✅ WebSocket endpoint with user_id path parameter
    
    Path Parameter:
    - user_id: User ID from path (required)
    
    Query Parameter:
    - token: JWT token from login (optional for extra security)
    
    Behavior:
    - Accepts WebSocket connections for specific user
    - Broadcasts order execution notifications
    - Broadcasts real-time price updates
    - Maintains connection until client disconnects
    
    Usage:
    ```
    ws://localhost:8000/ws/37
    ws://localhost:8000/ws/37?token=<JWT_TOKEN>  (with authentication)
    ```
    """
    try:
        # Verify user exists in database
        user = UserService.get_user(db, user_id)
        if not user:
            logger.warning(f"WebSocket connection rejected: User {user_id} not found")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            return
        
        # ✅ Optional: Validate JWT token if provided for extra security
        if token:
            try:
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                token_user_id = payload.get("sub")
                if not token_user_id or int(token_user_id) != user_id:
                    logger.warning(f"WebSocket token mismatch: Token user {token_user_id} != {user_id}")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token mismatch")
                    return
            except JWTError as e:
                logger.warning(f"Invalid JWT token for user {user_id}: {e}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
        
    except Exception as e:
        logger.error(f"WebSocket auth error for user {user_id}: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return
    
    # Accept connection
    await connection_manager.connect(user_id, websocket)
    logger.info(f"📡 WebSocket connected: user_id={user_id}")
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Echo back or handle any client messages (optional)
            if data:
                logger.debug(f"📨 Message from user {user_id}: {data}")
    
    except Exception as e:
        logger.info(f"⚠️  WebSocket error for user {user_id}: {e}")
    
    finally:
        await connection_manager.disconnect(user_id, websocket)
        logger.info(f"📡 WebSocket disconnected: user_id={user_id}")


# ============= ERROR HANDLERS =============
# ✅ NEW: Rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded exceptions"""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please try again later."}
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
