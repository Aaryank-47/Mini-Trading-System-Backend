"""System, health, and infrastructure API routes."""
from fastapi import APIRouter

from app.config import get_settings
from app.services.health_service import HealthService

router = APIRouter(tags=["System"])
settings = get_settings()


@router.get("/")
def root():
    """Root endpoint with API information."""
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
            "POST /redis/reconnect": "Trigger Redis reconnection",
        },
        "status": "running",
    }


@router.get("/health")
def health_check_endpoint():
    return HealthService.overall_health()


@router.get("/health/quick")
def health_quick_endpoint():
    return HealthService.quick_health()


@router.get("/health/detailed")
def health_detailed_endpoint():
    return HealthService.detailed_health()


@router.get("/health/database")
def health_database_endpoint():
    return HealthService.database_health()


@router.get("/health/redis")
def health_redis_endpoint():
    return HealthService.redis_health()


@router.get("/health/metrics")
def health_metrics_endpoint():
    return HealthService.metrics_health()


@router.get("/redis/status")
def redis_status_endpoint():
    return HealthService.redis_connection_status()


@router.post("/redis/reconnect")
def redis_reconnect_endpoint():
    return HealthService.reconnect_redis()
