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
from ...models.schemas import WatchlistResponse, WatchlistStock, AddStockRequest, RemoveStockRequest, UpdateStockStatusRequest, BulkStockActionRequest, SuccessResponse, MonitoringStatus
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
                status=MonitoringStatus.active if stock.status.value == 'active' else MonitoringStatus.paused,
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


@router.post("/update-status", response_model=SuccessResponse)
async def update_stock_status(
    request: UpdateStockStatusRequest,
    db: Annotated[Session, Depends(get_db)]
) -> SuccessResponse:
    """
    Update stock status (activate or deactivate).
    """
    try:
        # Validate input
        validate_ticker(request.ticker)
        ticker = request.ticker.upper()
        
        # Validate status
        if request.status not in ['active', 'inactive']:
            raise HTTPException(
                status_code=400,
                detail="Status must be 'active' or 'inactive'"
            )
        
        # Find the stock
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {ticker} not found in watchlist"
            )
        
        # Update status
        from ...models.stock import StockStatus
        stock.status = StockStatus(request.status)
        db.commit()
        
        logger.info(f"Updated {ticker} status to {request.status}")
        
        return SuccessResponse(
            success=True,
            message=f"Successfully updated {ticker} status to {request.status}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating stock status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update stock status: {str(e)}"
        )


@router.post("/bulk-action", response_model=SuccessResponse)
async def bulk_stock_action(
    request: BulkStockActionRequest,
    db: Annotated[Session, Depends(get_db)]
) -> SuccessResponse:
    """
    Perform bulk action on multiple stocks (activate, deactivate, or remove).
    """
    try:
        # Validate action
        if request.action not in ['activate', 'deactivate', 'remove']:
            raise HTTPException(
                status_code=400,
                detail="Action must be 'activate', 'deactivate', or 'remove'"
            )
        
        # Validate tickers
        tickers = []
        for ticker in request.tickers:
            validate_ticker(ticker)
            tickers.append(ticker.upper())
        
        # Find stocks
        stocks = db.query(Stock).filter(Stock.ticker.in_(tickers)).all()
        
        if not stocks:
            raise HTTPException(
                status_code=404,
                detail="No matching stocks found in watchlist"
            )
        
        processed_count = 0
        
        if request.action == 'remove':
            # Delete historical records and stocks
            for stock in stocks:
                db.query(HistoricalPremiumRecord)\
                    .filter(HistoricalPremiumRecord.stock_id == stock.stock_id)\
                    .delete()
                db.delete(stock)
                processed_count += 1
        else:
            # Update status
            from ...models.stock import StockStatus
            new_status = StockStatus.active if request.action == 'activate' else StockStatus.inactive
            
            for stock in stocks:
                stock.status = new_status
                processed_count += 1
        
        db.commit()
        
        logger.info(f"Bulk {request.action} completed for {processed_count} stocks")
        
        return SuccessResponse(
            success=True,
            message=f"Successfully {request.action}d {processed_count} stock(s)"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error performing bulk action: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform bulk action: {str(e)}"
        )
