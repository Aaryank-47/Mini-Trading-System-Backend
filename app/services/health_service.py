"""Service layer for health and infrastructure status responses."""
from datetime import datetime
from typing import Any, Dict

from app.utils.health_check import (
    HealthMetrics,
    check_database_health,
    check_redis_health,
    get_detailed_health_report,
    get_overall_health,
    get_quick_status,
    get_server_metrics,
)
from app.utils.redis_manager import (
    get_connection_status,
    health_check as redis_health_check,
    reconnect_redis,
)


class HealthService:
    """Provide health and infrastructure report payloads for API routes."""

    @staticmethod
    def overall_health() -> Dict[str, Any]:
        return get_overall_health()

    @staticmethod
    def quick_health() -> Dict[str, Any]:
        return get_quick_status()

    @staticmethod
    def detailed_health() -> Dict[str, Any]:
        return get_detailed_health_report()

    @staticmethod
    def database_health() -> Dict[str, Any]:
        status_info = check_database_health()
        return {
            "component": "database",
            "status": "Connected" if status_info["connected"] else "Disconnected",
            "details": status_info,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def redis_health() -> Dict[str, Any]:
        status_info = check_redis_health()
        return {
            "component": "redis",
            "status": status_info["connection_status"],
            "connected": status_info["connected"],
            "details": status_info["details"],
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def metrics_health() -> Dict[str, Any]:
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": HealthMetrics.get_uptime_seconds(),
            "uptime_formatted": HealthMetrics.get_uptime_formatted(),
            "requests_total": HealthMetrics.request_count,
            "errors_total": HealthMetrics.error_count,
            "error_rate_percent": round(
                (HealthMetrics.error_count / max(HealthMetrics.request_count, 1)) * 100,
                2,
            ) if HealthMetrics.request_count > 0 else 0,
            "server_resources": get_server_metrics(),
        }

    @staticmethod
    def redis_connection_status() -> Dict[str, Any]:
        return {
            "connection_status": get_connection_status(),
            "details": redis_health_check(),
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def reconnect_redis() -> Dict[str, Any]:
        success = reconnect_redis()
        return {
            "success": success,
            "status": get_connection_status(),
            "details": redis_health_check(),
            "timestamp": datetime.now().isoformat(),
        }
