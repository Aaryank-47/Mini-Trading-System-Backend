"""Main FastAPI application entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.lifespan import lifespan
from app.exceptions.handlers import register_exception_handlers
from app.middleware.http import register_http_middlewares
from app.routers import market, orders, portfolio, system, users, ws
from app.utils.rate_limiter import limiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()



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
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(portfolio.router)
app.include_router(market.router)
app.include_router(system.router)
app.include_router(ws.router)

register_http_middlewares(app)
register_exception_handlers(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
