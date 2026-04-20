"""
Comprehensive health check module for monitoring server and Redis status
"""
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from app.utils.redis_manager import health_check as redis_health_check, get_connection_status
from app.database import engine, SessionLocal
from sqlalchemy import text
import psutil
import os

logger = logging.getLogger(__name__)

# Track application metrics
class HealthMetrics:
    """Track application health metrics"""
    
    start_time = time.time()
    request_count = 0
    error_count = 0
    last_request_time = time.time()
    
    @classmethod
    def get_uptime_seconds(cls) -> int:
        """Get uptime in seconds"""
        return int(time.time() - cls.start_time)
    
    @classmethod
    def get_uptime_formatted(cls) -> str:
        """Get formatted uptime (e.g., '2d 3h 45m')"""
        seconds = cls.get_uptime_seconds()
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "< 1m"
    
    @classmethod
    def increment_requests(cls):
        """Increment request counter"""
        cls.request_count += 1
        cls.last_request_time = time.time()
    
    @classmethod
    def increment_errors(cls):
        """Increment error counter"""
        cls.error_count += 1


# ============= DATABASE HEALTH CHECKS =============
def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and status"""
    try:
        # Try to execute a simple query
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        return {
            "status": "healthy",
            "connected": True,
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "message": f"Database connection failed: {str(e)}"
        }


# ============= REDIS HEALTH CHECKS =============
def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and status"""
    redis_status = redis_health_check()
    connection_status = get_connection_status()
    
    return {
        "status": redis_status.get("status", "unhealthy"),
        "connected": redis_status.get("connected", False),
        "connection_status": connection_status,
        "details": redis_status
    }


# ============= SERVER HEALTH CHECKS =============
def get_server_metrics() -> Dict[str, Any]:
    """Get server resource metrics"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Process info
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        return {
            "cpu_percent": round(cpu_percent, 2),
            "memory": {
                "total_mb": round(memory.total / 1024 / 1024, 2),
                "used_mb": round(memory.used / 1024 / 1024, 2),
                "available_mb": round(memory.available / 1024 / 1024, 2),
                "percent": round(memory.percent, 2)
            },
            "process": {
                "rss_mb": round(process_memory.rss / 1024 / 1024, 2),
                "vms_mb": round(process_memory.vms / 1024 / 1024, 2),
                "num_threads": process.num_threads()
            }
        }
    except Exception as e:
        logger.warning(f"Failed to get server metrics: {e}")
        return {
            "cpu_percent": None,
            "memory": None,
            "process": None,
            "error": str(e)
        }


# ============= OVERALL HEALTH CHECK =============
def get_overall_health() -> Dict[str, Any]:
    """Get comprehensive health status for entire system"""
    
    # Check all components
    database = check_database_health()
    redis = check_redis_health()
    metrics = get_server_metrics()
    
    # Determine overall status
    if database["connected"] and redis["connected"]:
        overall_status = "healthy"
    elif database["connected"] and not redis["connected"]:
        overall_status = "degraded"  # Can work without Redis
    else:
        overall_status = "unhealthy"  # Database is critical
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "uptime": {
            "seconds": HealthMetrics.get_uptime_seconds(),
            "formatted": HealthMetrics.get_uptime_formatted()
        },
        "components": {
            "database": database,
            "redis": redis
        },
        "metrics": metrics,
        "requests": {
            "total": HealthMetrics.request_count,
            "errors": HealthMetrics.error_count,
            "last_request": datetime.fromtimestamp(HealthMetrics.last_request_time).isoformat()
        }
    }


# ============= DETAILED HEALTH REPORTS =============
def get_detailed_health_report() -> Dict[str, Any]:
    """Get detailed health report with all information"""
    
    database = check_database_health()
    redis = check_redis_health()
    metrics = get_server_metrics()
    
    # Status summary
    all_healthy = database["connected"] and redis["connected"]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "overall_status": "✅ Healthy" if all_healthy else "⚠️  Degraded" if database["connected"] else "❌ Unhealthy",
            "all_components_up": all_healthy,
            "can_accept_requests": database["connected"]
        },
        "application": {
            "uptime_seconds": HealthMetrics.get_uptime_seconds(),
            "uptime_formatted": HealthMetrics.get_uptime_formatted(),
            "total_requests": HealthMetrics.request_count,
            "error_requests": HealthMetrics.error_count,
            "error_rate_percent": round(
                (HealthMetrics.error_count / max(HealthMetrics.request_count, 1)) * 100, 2
            ) if HealthMetrics.request_count > 0 else 0
        },
        "database": {
            "status": "✅ Connected" if database["connected"] else "❌ Disconnected",
            "details": database
        },
        "redis": {
            "status": redis["connection_status"],
            "connected": redis["connected"],
            "details": redis["details"]
        },
        "server_resources": metrics,
        "health_checks": {
            "database_response": "✅" if database["connected"] else "❌",
            "redis_response": "✅" if redis["connected"] else "❌",
            "memory_available": "✅" if metrics.get("memory", {}).get("percent", 100) < 80 else "⚠️ " if metrics.get("memory", {}).get("percent", 100) < 90 else "❌",
            "cpu_normal": "✅" if metrics.get("cpu_percent", 0) < 80 else "⚠️ " if metrics.get("cpu_percent", 0) < 90 else "❌"
        }
    }


# ============= QUICK STATUS CHECK =============
def get_quick_status() -> Dict[str, Any]:
    """Get quick status check (minimal info, fast response)"""
    
    database = check_database_health()
    redis = check_redis_health()
    
    return {
        "status": "ok" if database["connected"] and redis["connected"] else "warning" if database["connected"] else "error",
        "database": "✅" if database["connected"] else "❌",
        "redis": "✅" if redis["connected"] else "❌",
        "uptime_seconds": HealthMetrics.get_uptime_seconds()
    }
