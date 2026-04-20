"""
Database module for SQLAlchemy ORM setup
Handles database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.config import get_settings
import asyncio
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

connect_args = {}
db_url = settings.db_url

if "sqlite" in db_url.lower():
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(
        db_url,
        poolclass=QueuePool if "sqlite" not in db_url.lower() else None,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
        connect_args=connect_args
    )
    engine.connect()
    logger.info(f"Successfully connected to database")
except Exception as e:
    logger.warning(f"Failed to connect to MySQL: {e}")
    logger.info("Falling back to SQLite for local development")
    db_url = "sqlite:///./trading.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        db_url,
        poolclass=None,
        pool_pre_ping=True,
        echo=False,
        connect_args=connect_args
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()


def get_db() -> Session:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
