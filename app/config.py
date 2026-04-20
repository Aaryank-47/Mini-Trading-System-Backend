"""
Configuration module for the Trading Platform API
Manages environment variables and app settings
"""
from functools import lru_cache
import os
from packaging import version
import pydantic

# Handle both pydantic 1.x and 2.x
if version.parse(pydantic.VERSION) >= version.parse("2.0.0"):
    from pydantic_settings import BaseSettings
else:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    environment: str = "LOCAL"
    
    app_name: str = "Trading Platform API"
    debug: bool = False
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    local_db_url: str = "mysql+pymysql://root:password@localhost/trading_db"
    neon_db_url: str = "postgresql://user:password@host/neondb?sslmode=require"
    db_url: str = "mysql+pymysql://root:password@localhost/trading_db"
    mysql_host: str = "localhost"
    mysql_user: str = "root"
    mysql_password: str = "password"
    mysql_database: str = "trading_db"
    
    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    def __init__(self, **data):
        """Initialize settings and select appropriate DB URL based on environment"""
        super().__init__(**data)
        if self.environment.upper() == "DEPLOYED":
            self.db_url = self.neon_db_url
        else:
            self.db_url = self.local_db_url


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
