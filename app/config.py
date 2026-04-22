"""
Configuration module for the Trading Platform API
Manages environment variables and app settings
Securely loads configuration from .env files and environment variables
"""
try:
    # Pydantic v2 provides a v1-compat namespace.
    from pydantic.v1 import BaseSettings, Field
except ImportError:
    # Fallback for pure Pydantic v1 environments.
    from pydantic import BaseSettings, Field
from functools import lru_cache
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    For local development: Create a .env file with your local secrets
    For production: Set environment variables in your platform (Render, Railway, etc.)
    """
    
    # Environment
    environment: str = Field(default="LOCAL", validation_alias="ENVIRONMENT")
    
    # App info
    app_name: str = "Trading Platform API"
    debug: bool = Field(default=False, validation_alias="DEBUG")
    allowed_origins: str = Field(default="*", validation_alias="ALLOWED_ORIGINS")
    
    # Security - MUST be set in environment, no default for production
    secret_key: str = Field(
        default="dev-secret-key-only-for-local-testing",
        validation_alias="SECRET_KEY",
        description="Secret key for JWT tokens - Change in production!"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database - Prefer Neon DB in deployed environments
    db_url: str = Field(default="", validation_alias="DB_URL")
    neon_db_url: str = Field(default="", validation_alias="NEON_DB_URL")
    mysql_host: str = Field(default="localhost", validation_alias="MYSQL_HOST")
    mysql_user: str = Field(default="root", validation_alias="MYSQL_USER")
    mysql_password: str = Field(default="password", validation_alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="trading_db", validation_alias="MYSQL_DATABASE")
    
    # Redis - Read from environment variables
    redis_url: str = Field(
        default="redis://localhost:6379",
        validation_alias="REDIS_URL",
        description="Redis connection URL"
    )
    redis_host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = 0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @property
    def database_url(self) -> str:
        """
        Resolve the active database URL.

        Priority:
        1. DB_URL environment variable
        2. NEON_DB_URL environment variable
        3. MySQL components for local development
        """
        if self.db_url:
            return self.db_url

        if self.neon_db_url:
            return self.neon_db_url

        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}/{self.mysql_database}"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses caching to avoid re-parsing .env file multiple times.
    """
    return Settings()
