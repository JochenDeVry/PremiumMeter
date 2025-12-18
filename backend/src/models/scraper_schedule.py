"""
Scraper Schedule model - Configuration for automated scraping
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, Time, Numeric
from sqlalchemy.sql import func
import enum
from datetime import datetime, time as dt_time
import pytz

from src.database.connection import Base


class SchedulerStatus(str, enum.Enum):
    """Scheduler status enumeration"""
    idle = "idle"
    running = "running"
    paused = "paused"
    error = "error"


class ScraperSchedule(Base):
    """
    Scraper Schedule entity - Configuration for automated scraping schedule
    
    Corresponds to spec.md Key Entities: Scraper Schedule
    Supports intra-day polling design with configurable intervals (1-60 minutes)
    """
    __tablename__ = "scraper_schedule"

    # Primary Key (single-row configuration table)
    schedule_id = Column(Integer, primary_key=True, autoincrement=True)
    
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
    
    # Black-Scholes Configuration
    risk_free_rate = Column(
        Numeric(5, 4),
        nullable=False,
        default=0.045,
        comment="Risk-free rate for Greeks calculation (e.g., 0.045 = 4.5%)"
    )
    
    # Status
    scheduler_status = Column(
        Enum(SchedulerStatus, name="scheduler_status"),
        default=SchedulerStatus.idle,
        nullable=False
    )
    
    # Execution Tracking
    last_run_timestamp = Column(DateTime(timezone=True))
    next_run_timestamp = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return (
            f"<ScraperSchedule("
            f"interval={self.polling_interval_minutes}min, "
            f"hours={self.market_hours_start}-{self.market_hours_end} {self.timezone}, "
            f"status='{self.scheduler_status.value}'"
            f")>"
        )
    
    def is_market_hours(self) -> bool:
        """
        Check if current time is within configured market hours.
        
        Returns:
            True if current time is within market hours window
        """
        # Get current time in configured timezone
        tz = pytz.timezone(self.timezone)
        now = datetime.now(tz)
        current_time = now.time()
        
        # Compare against configured market hours
        return self.market_hours_start <= current_time <= self.market_hours_end
