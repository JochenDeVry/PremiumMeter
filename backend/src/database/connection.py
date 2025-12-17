"""
Database connection setup for PostgreSQL + TimescaleDB.
Provides SQLAlchemy engine, session factory, and FastAPI dependency.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://premiummeter:changeme@localhost:5432/premiummeter"
)

# Create SQLAlchemy engine
# pool_pre_ping=True: verify connections before using (handle disconnects)
# pool_size=10: connection pool size for concurrent requests
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False  # Set to True for SQL query logging (development)
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
