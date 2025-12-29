"""
APScheduler Integration for Options Scraper

Manages scheduled scraping jobs with:
- Configurable polling intervals (intra-day: every 5 minutes default)
- Market hours enforcement (only scrape during market hours)
- Timezone-aware scheduling with DST handling
- Pause/resume capabilities
- Concurrency protection (max 1 instance)

References:
- research.md: APScheduler timezone strategy
- plan.md: FR-017 through FR-020 (polling, market hours, pause/resume, dynamic reconfiguration)
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from datetime import datetime, time
from typing import Optional
from sqlalchemy.orm import Session
import pytz
import logging

from ..models.scraper_schedule import ScraperSchedule, SchedulerStatus
from ..database.connection import get_db
from .scraper import create_scraper

logger = logging.getLogger(__name__)

# Global progress tracker
_scraper_progress = {
    "is_running": False,
    "total_stocks": 0,
    "completed_stocks": 0,
    "current_stock": None,
    "current_source": None,
    "pending_stocks": [],
    "completed_stock_list": [],
    "failed_stocks": [],
    "start_time": None,
    "estimated_completion": None
}


def get_scraper_progress():
    """Get current scraper progress"""
    return _scraper_progress.copy()


def update_scraper_progress(**kwargs):
    """Update scraper progress"""
    global _scraper_progress
    _scraper_progress.update(kwargs)


class SchedulerService:
    """
    Manages APScheduler for automated options scraping.
    
    Features:
    - Interval-based polling (configurable, default 5 minutes)
    - Market hours checking (skip scrapes outside market hours)
    - Timezone awareness with pytz (handles DST automatically)
    - Pause/resume without restart
    - Single instance execution (max_instances=1)
    """
    
    SCRAPER_JOB_ID = 'options_scraper'
    EXPIRY_MARKER_JOB_ID = 'expired_contract_marker'
    
    def __init__(self):
        """Initialize scheduler service"""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._is_initialized = False
    
    def initialize(self, db: Session) -> None:
        """
        Initialize APScheduler with configuration from database.
        
        Args:
            db: Database session to load ScraperSchedule configuration
        """
        if self._is_initialized:
            logger.warning("Scheduler already initialized")
            return
        
        logger.info("Initializing APScheduler")
        
        # Create scheduler instance
        self.scheduler = AsyncIOScheduler(timezone=pytz.UTC)
        
        # Load configuration from database
        config = self._load_config(db)
        
        if not config:
            logger.error("No ScraperSchedule configuration found in database")
            return
        
        # Start scheduler paused by default to prevent immediate rate limiting
        # User must manually start via API after adjusting watchlist size
        if config.scheduler_status != SchedulerStatus.paused:
            logger.warning("Setting scheduler to PAUSED on startup to prevent rate limiting")
            logger.warning("Rate limits: 60/min, 360/hour, 8000/day. Start manually after configuration.")
            config.scheduler_status = SchedulerStatus.paused
            db.commit()
        
        # Schedule main scraper job
        self._schedule_scraper_job(config)
        
        # Schedule expired contract marker (runs daily at midnight)
        self._schedule_expiry_marker_job(config)
        
        # Start scheduler
        self.scheduler.start()
        self._is_initialized = True
        
        logger.info(f"Scheduler initialized: polling_interval={config.polling_interval_minutes}min, "
                   f"market_hours={config.market_hours_start}-{config.market_hours_end} {config.timezone}, "
                   f"status={config.scheduler_status.value}")
    
    def shutdown(self) -> None:
        """Shutdown scheduler gracefully"""
        if self.scheduler and self.scheduler.running:
            logger.info("Shutting down scheduler")
            self.scheduler.shutdown(wait=True)
            self._is_initialized = False
    
    def pause(self, db: Session) -> None:
        """
        Pause scraper execution.
        
        Args:
            db: Database session to update configuration
        """
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        # Pause APScheduler job
        self.scheduler.pause_job(self.SCRAPER_JOB_ID)
        
        # Update database
        config = self._load_config(db)
        if config:
            config.scheduler_status = SchedulerStatus.paused
            db.commit()
        
        logger.info("Scheduler paused")
    
    def resume(self, db: Session) -> None:
        """
        Resume scraper execution.
        
        Args:
            db: Database session to update configuration
        """
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        # Resume APScheduler job
        self.scheduler.resume_job(self.SCRAPER_JOB_ID)
        
        # Update database
        config = self._load_config(db)
        if config:
            config.scheduler_status = SchedulerStatus.idle
            config.next_run_timestamp = self.get_next_run_time()
            db.commit()
        
        logger.info("Scheduler resumed")
    
    def update_config(
        self,
        db: Session,
        polling_interval_minutes: Optional[int] = None,
        market_hours_start: Optional[time] = None,
        market_hours_end: Optional[time] = None,
        timezone: Optional[str] = None
    ) -> None:
        """
        Update scheduler configuration and reschedule jobs.
        
        Args:
            db: Database session
            polling_interval_minutes: New polling interval (1-60 minutes)
            market_hours_start: New market open time
            market_hours_end: New market close time
            timezone: New timezone string (must be valid pytz timezone)
        """
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        # Load current config
        config = self._load_config(db)
        if not config:
            raise ValueError("No scheduler configuration found")
        
        # Update fields
        if polling_interval_minutes is not None:
            if not 1 <= polling_interval_minutes <= 1440:  # Up to 24 hours (1440 minutes)
                raise ValueError("Polling interval must be between 1 and 1440 minutes (24 hours)")
            config.polling_interval_minutes = polling_interval_minutes
        
        if market_hours_start is not None:
            config.market_hours_start = market_hours_start
        
        if market_hours_end is not None:
            config.market_hours_end = market_hours_end
        
        if timezone is not None:
            # Validate timezone
            if timezone not in pytz.all_timezones:
                raise ValueError(f"Invalid timezone: {timezone}")
            config.timezone = timezone
        
        # Validate market hours
        if config.market_hours_start >= config.market_hours_end:
            raise ValueError("Market hours start must be before market hours end")
        
        db.commit()
        
        # Reschedule jobs with new configuration
        self._reschedule_scraper_job(config)
        
        # Update next_run_timestamp after config change
        config.next_run_timestamp = self.get_next_run_time()
        db.commit()
        
        logger.info(f"Scheduler configuration updated: {config.polling_interval_minutes}min, "
                   f"{config.market_hours_start}-{config.market_hours_end} {config.timezone}")
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        Get next scheduled run time for scraper job.
        
        Returns:
            Next run datetime (None if not scheduled)
        """
        if not self.scheduler:
            return None
        
        job = self.scheduler.get_job(self.SCRAPER_JOB_ID)
        if job:
            return job.next_run_time
        return None
    
    def _load_config(self, db: Session) -> Optional[ScraperSchedule]:
        """Load ScraperSchedule configuration from database"""
        return db.query(ScraperSchedule).first()
    
    def _schedule_scraper_job(self, config: ScraperSchedule) -> None:
        """
        Schedule main scraper job with interval trigger.
        
        Args:
            config: ScraperSchedule configuration
        """
        # Create interval trigger (runs every N minutes)
        trigger = IntervalTrigger(
            minutes=config.polling_interval_minutes,
            timezone=pytz.timezone(config.timezone)
        )
        
        # Add job with concurrency protection
        self.scheduler.add_job(
            func=self._scraper_job_wrapper,
            trigger=trigger,
            id=self.SCRAPER_JOB_ID,
            name='Options Scraper',
            replace_existing=True,
            max_instances=1,  # Concurrency protection: only 1 instance at a time
            coalesce=True,    # If multiple runs missed, only run once
            misfire_grace_time=300  # 5 minutes grace period for missed runs
        )
        
        # Pause job if scheduler is paused
        if config.scheduler_status == SchedulerStatus.paused:
            self.scheduler.pause_job(self.SCRAPER_JOB_ID)
        
        logger.info(f"Scheduled scraper job: interval={config.polling_interval_minutes}min, max_instances=1")
    
    def _schedule_expiry_marker_job(self, config: ScraperSchedule) -> None:
        """
        Schedule daily expired contract marker job.
        
        Args:
            config: ScraperSchedule configuration
        """
        # Run daily at midnight in configured timezone
        trigger = CronTrigger(
            hour=0,
            minute=0,
            timezone=pytz.timezone(config.timezone)
        )
        
        self.scheduler.add_job(
            func=self._expiry_marker_job_wrapper,
            trigger=trigger,
            id=self.EXPIRY_MARKER_JOB_ID,
            name='Expired Contract Marker',
            replace_existing=True,
            max_instances=1
        )
        
        logger.info("Scheduled expired contract marker: daily at midnight")
    
    def _reschedule_scraper_job(self, config: ScraperSchedule) -> None:
        """
        Reschedule scraper job with updated configuration.
        
        Args:
            config: Updated ScraperSchedule configuration
        """
        # Create new trigger
        trigger = IntervalTrigger(
            minutes=config.polling_interval_minutes,
            timezone=pytz.timezone(config.timezone)
        )
        
        # Reschedule job
        self.scheduler.reschedule_job(
            job_id=self.SCRAPER_JOB_ID,
            trigger=trigger
        )
        
        logger.info(f"Rescheduled scraper job: interval={config.polling_interval_minutes}min")
    
    def _scraper_job_wrapper(self) -> None:
        """
        Wrapper for scraper job that checks market hours before execution.
        
        This function is called by APScheduler on the configured interval.
        It checks if current time is within market hours before scraping.
        """
        # Get database session
        db = next(get_db())
        
        try:
            # Load configuration
            config = self._load_config(db)
            if not config:
                logger.error("No scheduler configuration found")
                return
            
            # Check if within market hours
            if not config.is_market_hours():
                logger.debug(f"Outside market hours ({config.market_hours_start}-{config.market_hours_end}), skipping scrape")
                return
            
            # Update status to running
            config.scheduler_status = SchedulerStatus.running
            config.last_run_timestamp = datetime.now()
            db.commit()
            
            logger.info("Starting scheduled scrape (within market hours)")
            
            # Execute scraper
            scraper = create_scraper(db)
            metrics = scraper.scrape_all_stocks()
            
            # Log execution metrics (T035)
            logger.info(f"Scrape completed: {metrics.successful_stocks}/{metrics.total_stocks} stocks, "
                       f"{metrics.total_contracts} contracts, "
                       f"{metrics.duration_seconds():.2f}s, "
                       f"{metrics.to_dict()['contracts_per_stock']} contracts/stock avg")
            
            if metrics.failed_stocks > 0:
                logger.warning(f"Scrape had {metrics.failed_stocks} failures: {metrics.stock_errors}")
            
            # Update status back to idle
            config.scheduler_status = SchedulerStatus.idle
            config.next_run_timestamp = self.get_next_run_time()
            db.commit()
        
        except Exception as e:
            logger.error(f"Scraper job failed: {e}", exc_info=True)
            
            # Update status to error
            config = self._load_config(db)
            if config:
                config.scheduler_status = SchedulerStatus.error
                db.commit()
        
        finally:
            db.close()
    
    def _expiry_marker_job_wrapper(self) -> None:
        """
        Wrapper for expired contract marker job.
        
        Runs daily at midnight to mark contracts past expiration_date as expired.
        """
        db = next(get_db())
        
        try:
            logger.info("Starting expired contract marker")
            
            scraper = create_scraper(db)
            count = scraper.mark_expired_contracts()
            
            logger.info(f"Expired contract marker completed: {count} contracts marked")
        
        except Exception as e:
            logger.error(f"Expired contract marker failed: {e}", exc_info=True)
        
        finally:
            db.close()


# Global singleton instance
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    """
    Get or create the singleton SchedulerService instance.
    
    Returns:
        SchedulerService instance
    """
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
