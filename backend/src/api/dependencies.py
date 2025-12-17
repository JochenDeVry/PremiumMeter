"""
FastAPI dependency injection providers.
Provides reusable dependencies for API endpoints.
"""

from fastapi import Depends
from sqlalchemy.orm import Session
from src.database.connection import get_db

# Database session dependency
# Usage in endpoints:
#   @router.get("/items")
#   def read_items(db: Session = Depends(get_database_session)):
#       return db.query(Item).all()

def get_database_session() -> Session:
    """
    Dependency that provides database session.
    Alias for get_db() for clearer endpoint signatures.
    """
    return get_db()

__all__ = ["get_database_session", "get_db"]
