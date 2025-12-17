"""
SQLAlchemy ORM models initialization.
Imports all models to ensure they're registered with Base.metadata.
"""

from src.database.connection import Base

# Import all models here so Alembic can detect them
# Models will be created in domain.py as part of Phase 3
__all__ = ["Base"]
