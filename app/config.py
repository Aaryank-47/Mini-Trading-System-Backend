"""
Configuration module for the Trading Platform API
Manages environment variables and app settings
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # App Configuration
    app_name: str = "Trading Platform API"
    debug: bool = True
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database Configuration
    db_url: str = "mysql+pymysql://root:password@localhost/trading_db"
    mysql_host: str = "localhost"
    mysql_user: str = "root"
    mysql_password: str = "password"
    mysql_database: str = "trading_db"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
