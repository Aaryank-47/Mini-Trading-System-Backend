"""Application-wide exception handler registration."""
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded responses."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please try again later."},
    )


async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions as bad requests."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions consistently."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register app-level exception handlers."""
    app.exception_handler(RateLimitExceeded)(rate_limit_handler)
    app.exception_handler(ValueError)(value_error_handler)
    app.exception_handler(Exception)(general_exception_handler)
