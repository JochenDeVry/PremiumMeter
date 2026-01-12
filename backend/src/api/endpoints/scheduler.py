"""
Scheduler API Endpoints

Handles scheduler configuration and control (pause/resume, update config).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
import logging
import pytz

from ...database.connection import get_db
from ...models.schemas import (
    SchedulerConfig, SchedulerConfigRequest, SuccessResponse, SchedulerStatus, 
    RateLimitCalculation, ScraperProgress, ScraperRunHistoryResponse, ScraperRunSchema, StockScrapeLogSchema
)
from ...services.scheduler import get_scheduler_service
from ...utils.security import validate_integer_range

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/config", response_model=SchedulerConfig)
async def get_scheduler_config(
    db: Annotated[Session, Depends(get_db)]
) -> SchedulerConfig:
    """
    Get the current scheduler configuration.
    """
    try:
        scheduler_service = get_scheduler_service()
        
        # Load config from database
        from ...models.scraper_schedule import ScraperSchedule
        config = db.query(ScraperSchedule).first()
        
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Scheduler configuration not found"
            )
        
        # Return actual scheduler status from database
        status = SchedulerStatus(config.scheduler_status.value)
        
        return SchedulerConfig(
            polling_interval_minutes=config.polling_interval_minutes,
            market_hours_start=config.market_hours_start.isoformat() if hasattr(config.market_hours_start, 'isoformat') else str(config.market_hours_start),
            market_hours_end=config.market_hours_end.isoformat() if hasattr(config.market_hours_end, 'isoformat') else str(config.market_hours_end),
            timezone=config.timezone,
            exclude_weekends=True,  # Hardcoded defaults since not in DB model
            exclude_holidays=True,
            status=status,
            next_run=scheduler_service.get_next_run_time().isoformat() if scheduler_service.get_next_run_time() else None,
            last_run=None,  # TODO: Track last run time
            stock_delay_seconds=config.stock_delay_seconds,
            max_expirations=config.max_expirations
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching scheduler config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve scheduler configuration: {str(e)}"
        )


@router.put("/config", response_model=SchedulerConfig)
async def update_scheduler_config(
    request: SchedulerConfigRequest,
    db: Annotated[Session, Depends(get_db)]
) -> SchedulerConfig:
    """
    Update the scheduler configuration.
    """
    try:
        # Validate inputs
        if request.polling_interval_minutes is not None:
            validate_integer_range(request.polling_interval_minutes, min_value=1, max_value=1440, field_name="polling_interval_minutes")
        if request.stock_delay_seconds is not None:
            validate_integer_range(request.stock_delay_seconds, min_value=0, max_value=300, field_name="stock_delay_seconds")
        if request.max_expirations is not None:
            validate_integer_range(request.max_expirations, min_value=1, max_value=100, field_name="max_expirations")
        if request.timezone is not None:
            # Validate timezone
            try:
                pytz.timezone(request.timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                raise HTTPException(status_code=400, detail=f"Invalid timezone: {request.timezone}")
        
        from ...models.scraper_schedule import ScraperSchedule
        
        config = db.query(ScraperSchedule).first()
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Scheduler configuration not found"
            )
        
        # Update fields if provided
        if request.polling_interval_minutes is not None:
            config.polling_interval_minutes = request.polling_interval_minutes
        if request.market_hours_start is not None:
            from datetime import time
            h, m = map(int, request.market_hours_start.split(':'))
            config.market_hours_start = time(hour=h, minute=m)
        if request.market_hours_end is not None:
            from datetime import time
            h, m = map(int, request.market_hours_end.split(':'))
            config.market_hours_end = time(hour=h, minute=m)
        if request.timezone is not None:
            config.timezone = request.timezone
        if request.stock_delay_seconds is not None:
            config.stock_delay_seconds = request.stock_delay_seconds
        if request.max_expirations is not None:
            config.max_expirations = request.max_expirations
        # exclude_weekends and exclude_holidays not in DB model yet
        
        db.commit()
        db.refresh(config)
        
        # Update scheduler service if settings changed and scheduler is running
        scheduler_service = get_scheduler_service()
        if request.polling_interval_minutes is not None and scheduler_service.scheduler:
            try:
                scheduler_service.update_config(
                    db=db,
                    polling_interval_minutes=request.polling_interval_minutes
                )
            except Exception as sched_err:
                logger.warning(f"Could not update running scheduler: {sched_err}")
                # Continue - settings are saved in DB and will apply on next scheduler restart
        
        logger.info(f"Updated scheduler configuration")
        
        # Return updated config
        scheduler_service = get_scheduler_service()
        is_running = scheduler_service.scheduler and scheduler_service.scheduler.running
        status = MonitoringStatus.active if is_running and config.scheduler_status.value != 'paused' else MonitoringStatus.paused
        
        return SchedulerConfig(
            polling_interval_minutes=config.polling_interval_minutes,
            market_hours_start=config.market_hours_start.isoformat() if hasattr(config.market_hours_start, 'isoformat') else str(config.market_hours_start),
            market_hours_end=config.market_hours_end.isoformat() if hasattr(config.market_hours_end, 'isoformat') else str(config.market_hours_end),
            timezone=config.timezone,
            exclude_weekends=True,  # Hardcoded defaults
            exclude_holidays=True,
            status=status,
            next_run=scheduler_service.get_next_run_time().isoformat() if scheduler_service.get_next_run_time() else None,
            last_run=None,
            stock_delay_seconds=config.stock_delay_seconds,
            max_expirations=config.max_expirations
        )
    
    except Exception as e:
        logger.error(f"Error updating scheduler config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update scheduler configuration: {str(e)}"
        )


@router.post("/pause", response_model=SuccessResponse)
async def pause_scheduler(
    db: Annotated[Session, Depends(get_db)]
) -> SuccessResponse:
    """
    Pause the scheduler (stop automatic data collection).
    """
    try:
        scheduler_service = get_scheduler_service()
        scheduler_service.pause(db)
        
        logger.info("Scheduler paused")
        
        return SuccessResponse(
            success=True,
            message="Scheduler paused successfully"
        )
    
    except Exception as e:
        logger.error(f"Error pausing scheduler: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pause scheduler: {str(e)}"
        )


@router.post("/resume", response_model=SuccessResponse)
async def resume_scheduler(
    db: Annotated[Session, Depends(get_db)],
    start_now: bool = False
) -> SuccessResponse:
    """
    Resume the scheduler (restart automatic data collection).
    
    Args:
        start_now: If True, trigger an immediate scrape run before scheduling
    """
    try:
        scheduler_service = get_scheduler_service()
        scheduler_service.resume(db)
        
        # If start_now is True, trigger immediate scrape
        if start_now:
            logger.info("Triggering immediate scrape run")
            # Run scraper in background
            import threading
            thread = threading.Thread(target=scheduler_service._scraper_job_wrapper)
            thread.daemon = True
            thread.start()
        
        logger.info("Scheduler resumed")
        
        return SuccessResponse(
            success=True,
            message="Scheduler resumed successfully" + (" and immediate scrape started" if start_now else "")
        )
    
    except Exception as e:
        logger.error(f"Error resuming scheduler: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume scheduler: {str(e)}"
        )


@router.get("/rate-calculation", response_model=RateLimitCalculation)
async def calculate_rate_limits(
    db: Annotated[Session, Depends(get_db)],
    polling_interval_minutes: int = None,
    stock_delay_seconds: int = None,
    max_expirations: int = None
) -> RateLimitCalculation:
    """
    Calculate expected API request rates based on configuration and watchlist.
    If parameters provided, uses those for calculation; otherwise uses current DB config.
    Returns rate limit compliance status and warnings.
    """
    try:
        from ...models.scraper_schedule import ScraperSchedule
        from ...models.stock import Stock, StockStatus
        
        # Load config from DB
        config = db.query(ScraperSchedule).first()
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Scheduler configuration not found"
            )
        
        # Use provided parameters or fall back to DB config
        interval = polling_interval_minutes if polling_interval_minutes is not None else config.polling_interval_minutes
        delay = stock_delay_seconds if stock_delay_seconds is not None else config.stock_delay_seconds
        max_exp = max_expirations if max_expirations is not None else config.max_expirations
        
        # Get active stocks count (only active stocks are scraped)
        watchlist_size = db.query(Stock).filter(
            Stock.status == StockStatus.active
        ).count()
        
        # Calculate requests per stock: 1 price + 1 expirations + N option chains
        requests_per_stock = 2 + max_exp
        
        # Calculate per-cycle metrics
        requests_per_cycle = watchlist_size * requests_per_stock
        cycle_duration_minutes = (watchlist_size * delay) / 60.0
        
        # Calculate per-minute rate
        requests_per_minute = requests_per_cycle / cycle_duration_minutes if cycle_duration_minutes > 0 else requests_per_cycle
        
        # Calculate per-hour metrics
        cycles_per_hour = 60.0 / interval if interval > 0 else 0
        requests_per_hour = requests_per_cycle * cycles_per_hour
        
        # Calculate per-day metrics
        cycles_per_day = int((24 * 60) / interval) if interval > 0 else 0
        requests_per_day = requests_per_cycle * cycles_per_day
        
        # Check limits (Yahoo: 60/min, 360/hour, 8000/day)
        within_minute_limit = requests_per_minute <= 60
        within_hour_limit = requests_per_hour <= 360
        within_day_limit = requests_per_day <= 8000
        
        # Generate warnings
        warnings = []
        if not within_minute_limit:
            warnings.append(f"Exceeds 60 requests/min limit: {requests_per_minute:.1f}/min")
        if not within_hour_limit:
            warnings.append(f"Exceeds 360 requests/hour limit: {requests_per_hour:.0f}/hour")
        if not within_day_limit:
            warnings.append(f"Exceeds 8000 requests/day limit: {requests_per_day:.0f}/day")
        
        # Add recommendations
        if not within_day_limit:
            max_stocks_for_day = int(8000 / (requests_per_stock * cycles_per_day)) if cycles_per_day > 0 else 0
            warnings.append(f"Recommendation: Reduce watchlist to {max_stocks_for_day} stocks or increase interval")
        elif not within_hour_limit:
            recommended_interval = int((requests_per_cycle * 60) / 360) if requests_per_cycle > 0 else interval
            warnings.append(f"Recommendation: Increase interval to {recommended_interval}+ minutes or reduce watchlist")
        
        # Check if counter needs reset and get current values
        config.check_and_reset_daily_counter()
        db.commit()
        
        return RateLimitCalculation(
            watchlist_size=watchlist_size,
            requests_per_stock=requests_per_stock,
            requests_per_cycle=requests_per_cycle,
            cycle_duration_minutes=round(cycle_duration_minutes, 2),
            requests_per_minute=round(requests_per_minute, 1),
            cycles_per_hour=round(cycles_per_hour, 2),
            requests_per_hour=round(requests_per_hour, 0),
            cycles_per_day=cycles_per_day,
            requests_per_day=requests_per_day,
            within_minute_limit=within_minute_limit,
            within_hour_limit=within_hour_limit,
            within_day_limit=within_day_limit,
            warnings=warnings,
            actual_queries_today=config.daily_api_queries,
            last_reset_time=config.last_reset_date.isoformat() if config.last_reset_date else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating rate limits: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate rate limits: {str(e)}"
        )


@router.get("/progress", response_model=ScraperProgress)
async def get_scraper_progress() -> ScraperProgress:
    """
    Get current scraper progress.
    """
    try:
        from ...services.scheduler import get_scraper_progress
        
        progress = get_scraper_progress()
        
        return ScraperProgress(
            is_running=progress["is_running"],
            total_stocks=progress["total_stocks"],
            completed_stocks=progress["completed_stocks"],
            current_stock=progress["current_stock"],
            current_source=progress["current_source"],
            pending_stocks=progress["pending_stocks"],
            completed_stock_list=progress["completed_stock_list"],
            failed_stocks=progress["failed_stocks"],
            start_time=progress["start_time"],
            estimated_completion=progress["estimated_completion"]
        )
    
    except Exception as e:
        logger.error(f"Error getting scraper progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scraper progress: {str(e)}"
        )


@router.get("/run-history", response_model=ScraperRunHistoryResponse)
async def get_run_history(
    db: Annotated[Session, Depends(get_db)],
    limit: int = 20
) -> ScraperRunHistoryResponse:
    """
    Get scraper run history with detailed logs.
    Returns last N runs (default 20) with stock-by-stock details.
    """
    try:
        from ...models.scraper_run_log import ScraperRun, ScraperStockLog
        
        # Query recent runs, ordered by start time descending
        runs = (
            db.query(ScraperRun)
            .order_by(ScraperRun.start_time.desc())
            .limit(min(limit, 50))  # Cap at 50 runs max
            .all()
        )
        
        # Convert to response schema
        run_schemas = []
        for run in runs:
            # Get stock logs for this run
            stock_logs = (
                db.query(ScraperStockLog)
                .filter(ScraperStockLog.run_id == run.id)
                .order_by(ScraperStockLog.timestamp)
                .all()
            )
            
            stock_log_schemas = [
                StockScrapeLogSchema(
                    ticker=log.ticker,
                    status=log.status.value,
                    source_used=log.source_used,
                    contracts_scraped=log.contracts_scraped,
                    timestamp=log.timestamp.isoformat(),
                    error_message=log.error_message
                )
                for log in stock_logs
            ]
            
            run_schemas.append(
                ScraperRunSchema(
                    id=run.id,
                    start_time=run.start_time.isoformat(),
                    end_time=run.end_time.isoformat() if run.end_time else None,
                    status=run.status.value,
                    total_stocks=run.total_stocks,
                    successful_stocks=run.successful_stocks,
                    failed_stocks=run.failed_stocks,
                    total_contracts=run.total_contracts,
                    stock_logs=stock_log_schemas
                )
            )
        
        total_count = db.query(ScraperRun).count()
        
        return ScraperRunHistoryResponse(
            runs=run_schemas,
            total_count=total_count
        )
    
    except Exception as e:
        logger.error(f"Error getting run history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get run history: {str(e)}"
        )
