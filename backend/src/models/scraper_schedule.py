"""
Scraper Schedule model - Configuration for automated scraping
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Time
from sqlalchemy.sql import func
import enum

from src.database.connection import Base


class SchedulerStatus(str, enum.Enum):
    """Scheduler status enumeration"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class ScraperSchedule(Base):
    """
    Scraper Schedule entity - Configuration for automated scraping schedule
    
    Corresponds to spec.md Key Entities: Scraper Schedule
    Supports intra-day polling design with configurable intervals (1-60 minutes)
    """
    __tablename__ = "scraper_schedule"

    # Primary Key (single-row configuration table)
    config_id = Column(Integer, primary_key=True, default=1)
    
    # Polling Configuration
    polling_interval_minutes = Column(
        Integer,
        nullable=False,
        default=5,  # Default: 5 minutes (intra-day polling)
        comment="Polling interval in minutes (1-60)"
    )
    
    # Market Hours Configuration (timezone-aware)
    market_hours_start = Column(
        Time,
        nullable=False,
        default="09:30:00",  # 9:30 AM ET
        comment="Market hours start time"
    )
    market_hours_end = Column(
        Time,
        nullable=False,
        default="16:00:00",  # 4:00 PM ET
        comment="Market hours end time"
    )
    timezone = Column(
        String(50),
        nullable=False,
        default="America/New_York",
        comment="Timezone for market hours (IANA timezone)"
    )
    
    # Exclusion Rules
    exclude_weekends = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Skip polling on weekends"
    )
    exclude_holidays = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Skip polling on market holidays"
    )
    
    # Status
    status = Column(
        Enum(SchedulerStatus, name="scheduler_status"),
        default=SchedulerStatus.IDLE,
        nullable=False
    )
    
    # Execution Tracking
    next_run_at = Column(DateTime(timezone=True))
    last_run_at = Column(DateTime(timezone=True))
    last_error_message = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return (
            f"<ScraperSchedule("
            f"interval={self.polling_interval_minutes}min, "
            f"hours={self.market_hours_start}-{self.market_hours_end} {self.timezone}, "
            f"status='{self.status.value}'"
            f")>"
        )
    
    @staticmethod
    def ensure_single_row():
        """
        Validation constraint: Only one configuration row allowed
        Enforced at application level (can also use CHECK constraint in PostgreSQL)
        """
        return "config_id = 1"
