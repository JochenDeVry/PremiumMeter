"""
SQLAlchemy ORM models initialization.
Imports all models to ensure they're registered with Base.metadata.
"""

from src.database.connection import Base

# Import domain models for Alembic autodiscovery
from src.models.stock import Stock, StockStatus
from src.models.historical_premium_record import (
    HistoricalPremiumRecord,
    OptionType,
    ContractStatus,
)
from src.models.watchlist import Watchlist, MonitoringStatus
from src.models.scraper_schedule import ScraperSchedule, SchedulerStatus

__all__ = [
    "Base",
    "Stock",
    "StockStatus",
    "HistoricalPremiumRecord",
    "OptionType",
    "ContractStatus",
    "Watchlist",
    "MonitoringStatus",
    "ScraperSchedule",
    "SchedulerStatus",
]

