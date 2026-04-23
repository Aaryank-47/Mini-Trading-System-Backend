"""HTTP middleware registration and handlers."""
import logging

from fastapi import FastAPI, Request

from app.config import get_settings
from app.utils.health_check import HealthMetrics

logger = logging.getLogger(__name__)
settings = get_settings()


async def add_security_headers(request: Request, call_next):
    """Add security-related response headers to all HTTP requests."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    if not settings.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"

    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


async def track_requests(request: Request, call_next):
    """Track request and error counts used by health metrics."""
    try:
        HealthMetrics.increment_requests()
        response = await call_next(request)

        if response.status_code >= 500:
            HealthMetrics.increment_errors()

        return response
    except Exception as exc:
        HealthMetrics.increment_errors()
        logger.error(f"Request error: {exc}")
        raise


def register_http_middlewares(app: FastAPI) -> None:
    """Register all HTTP middlewares for the FastAPI app."""
    app.middleware("http")(add_security_headers)
    app.middleware("http")(track_requests)
