"""
Scheduler API Endpoints

Handles scheduler configuration and control (pause/resume, update config).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
import logging

from ...database.connection import get_db
from ...models.schemas import SchedulerConfig, SchedulerConfigRequest, SuccessResponse, MonitoringStatus
from ...services.scheduler import get_scheduler_service

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
        
        # Determine if scheduler is running
        is_running = scheduler_service.scheduler and scheduler_service.scheduler.running
        status = MonitoringStatus.active if is_running and config.scheduler_status.value != 'paused' else MonitoringStatus.paused
        
        return SchedulerConfig(
            polling_interval_minutes=config.polling_interval_minutes,
            market_hours_start=config.market_hours_start.isoformat() if hasattr(config.market_hours_start, 'isoformat') else str(config.market_hours_start),
            market_hours_end=config.market_hours_end.isoformat() if hasattr(config.market_hours_end, 'isoformat') else str(config.market_hours_end),
            timezone=config.timezone,
            exclude_weekends=True,  # Hardcoded defaults since not in DB model
            exclude_holidays=True,
            status=status,
            next_run=scheduler_service.get_next_run_time().isoformat() if scheduler_service.get_next_run_time() else None,
            last_run=None  # TODO: Track last run time
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
        # exclude_weekends and exclude_holidays not in DB model yet
        
        db.commit()
        db.refresh(config)
        
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
            last_run=None
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
    db: Annotated[Session, Depends(get_db)]
) -> SuccessResponse:
    """
    Resume the scheduler (restart automatic data collection).
    """
    try:
        scheduler_service = get_scheduler_service()
        scheduler_service.resume(db)
        
        logger.info("Scheduler resumed")
        
        return SuccessResponse(
            success=True,
            message="Scheduler resumed successfully"
        )
    
    except Exception as e:
        logger.error(f"Error resuming scheduler: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume scheduler: {str(e)}"
        )
