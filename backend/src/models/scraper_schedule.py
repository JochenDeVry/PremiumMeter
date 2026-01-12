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
    
    # Rate Limiting Configuration
    stock_delay_seconds = Column(
        Integer,
        nullable=False,
        default=10,
        comment="Delay between scraping stocks (seconds) - helps avoid rate limiting"
    )
    max_expirations = Column(
        Integer,
        nullable=False,
        default=8,
        comment="Maximum number of option expirations to fetch per stock (nearest dates)"
    )
    
    # Daily Query Counter (resets at 7:30 AM EST)
    daily_api_queries = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Count of API queries made today (resets at 7:30 AM EST)"
    )
    last_reset_date = Column(
        DateTime(timezone=True),
        comment="Last time the daily counter was reset"
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
    
    def check_and_reset_daily_counter(self) -> bool:
        """
        Check if daily counter needs to be reset (at 7:30 AM EST / 1:30 PM Brussels).
        Resets counter if it's a new day past 7:30 AM EST.
        
        Returns:
            True if counter was reset, False otherwise
        """
        # Reset time is 7:30 AM EST (two hours before market open at 9:30 AM)
        reset_time = dt_time(7, 30, 0)
        est_tz = pytz.timezone('America/New_York')
        now_est = datetime.now(est_tz)
        current_time_est = now_est.time()
        current_date_est = now_est.date()
        
        # If no last_reset_date, initialize it
        if self.last_reset_date is None:
            self.last_reset_date = now_est
            self.daily_api_queries = 0
            return True
        
        # Convert last_reset to EST for comparison
        last_reset_est = self.last_reset_date.astimezone(est_tz)
        last_reset_date_est = last_reset_est.date()
        
        # Check if it's a new day and we've passed 7:30 AM EST
        if current_date_est > last_reset_date_est:
            # It's a new day - check if we've passed reset time
            if current_time_est >= reset_time:
                self.daily_api_queries = 0
                self.last_reset_date = now_est
                return True
            # If it's a new day but before reset time, check if yesterday's reset was done
            elif last_reset_date_est < current_date_est:
                # Yesterday we didn't reset yet, so do it now
                self.daily_api_queries = 0
                self.last_reset_date = now_est
                return True
        elif current_date_est == last_reset_date_est:
            # Same day - check if last reset was before 7:30 AM and now it's after
            if last_reset_est.time() < reset_time and current_time_est >= reset_time:
                self.daily_api_queries = 0
                self.last_reset_date = now_est
                return True
        
        return False
    
    def increment_query_count(self, count: int = 1) -> None:
        """
        Increment the daily API query counter.
        
        Args:
            count: Number of queries to add (default: 1)
        """
        # Check if counter needs reset before incrementing
        self.check_and_reset_daily_counter()
        self.daily_api_queries += count
