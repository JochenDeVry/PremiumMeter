"""
Watchlist API Endpoints

Handles stock watchlist management (add/remove stocks, view watchlist).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
import logging

from ...database.connection import get_db
from ...models.stock import Stock
from ...models.historical_premium_record import HistoricalPremiumRecord
from ...models.schemas import WatchlistResponse, WatchlistStock, AddStockRequest, RemoveStockRequest, SuccessResponse, MonitoringStatus
from ...utils.security import validate_ticker, sanitize_string
from sqlalchemy import func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    db: Annotated[Session, Depends(get_db)]
) -> WatchlistResponse:
    """
    Get the current stock watchlist with data collection statistics.
    """
    try:
        # Query all stocks with their data point counts
        stocks = db.query(Stock).all()
        
        watchlist_items = []
        for stock in stocks:
            # Count historical data points
            data_points = db.query(func.count(HistoricalPremiumRecord.record_id))\
                .filter(HistoricalPremiumRecord.stock_id == stock.stock_id)\
                .scalar() or 0
            
            # Get last scraped timestamp
            last_record = db.query(HistoricalPremiumRecord)\
                .filter(HistoricalPremiumRecord.stock_id == stock.stock_id)\
                .order_by(HistoricalPremiumRecord.collection_timestamp.desc())\
                .first()
            
            watchlist_items.append(WatchlistStock(
                stock_id=stock.stock_id,
                ticker=stock.ticker,
                company_name=stock.company_name or "",
                status=MonitoringStatus.active,  # Default to active
                added_at=stock.created_at.isoformat() if stock.created_at else "",
                last_scraped=last_record.collection_timestamp.isoformat() if last_record else None,
                data_points_count=data_points
            ))
        
        return WatchlistResponse(
            watchlist=watchlist_items,
            total_count=len(watchlist_items)
        )
    
    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve watchlist: {str(e)}"
        )


@router.post("/add", response_model=SuccessResponse)
async def add_stock_to_watchlist(
    request: AddStockRequest,
    db: Annotated[Session, Depends(get_db)]
) -> SuccessResponse:
    """
    Add a stock ticker to the watchlist for monitoring.
    """
    try:
        # Validate and sanitize inputs
        validate_ticker(request.ticker)
        ticker = request.ticker.upper()
        
        # Check if stock already exists
        existing_stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if existing_stock:
            return SuccessResponse(
                success=True,
                message=f"Stock {ticker} is already in the watchlist"
            )
        
        # Create new stock entry
        company_name = sanitize_string(request.company_name, max_length=255) if request.company_name else ticker
        new_stock = Stock(
            ticker=ticker,
            company_name=company_name
        )
        db.add(new_stock)
        db.commit()
        db.refresh(new_stock)
        
        logger.info(f"Added {ticker} to watchlist")
        
        return SuccessResponse(
            success=True,
            message=f"Successfully added {ticker} to watchlist"
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding stock to watchlist: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add stock: {str(e)}"
        )


@router.delete("/remove", response_model=SuccessResponse)
async def remove_stock_from_watchlist(
    request: RemoveStockRequest,
    db: Annotated[Session, Depends(get_db)]
) -> SuccessResponse:
    """
    Remove a stock ticker from the watchlist.
    """
    try:
        # Validate input
        validate_ticker(request.ticker)
        ticker = request.ticker.upper()
        
        # Find the stock
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {ticker} not found in watchlist"
            )
        
        # Delete associated historical records first (foreign key constraint)
        db.query(HistoricalPremiumRecord)\
            .filter(HistoricalPremiumRecord.stock_id == stock.stock_id)\
            .delete()
        
        # Delete the stock
        db.delete(stock)
        db.commit()
        
        logger.info(f"Removed {ticker} from watchlist")
        
        return SuccessResponse(
            success=True,
            message=f"Successfully removed {ticker} from watchlist"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing stock from watchlist: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove stock: {str(e)}"
        )
