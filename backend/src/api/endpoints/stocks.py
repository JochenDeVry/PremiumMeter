"""
Stocks API Endpoints

Handles stock information retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated, List, Optional
import logging
from datetime import datetime, timedelta

from ...database.connection import get_db
from ...models.stock import Stock
from ...models.historical_premium_record import HistoricalPremiumRecord
from ...services.stock_price_service import get_stock_price_service
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

# Price cache to avoid redundant API calls
# Structure: {ticker: {"price": float, "timestamp": datetime, "source": str}}
_price_cache = {}
_cache_ttl_minutes = 10  # Cache prices for 10 minutes


class StockInfo(BaseModel):
    """Basic stock information"""
    ticker: str
    company_name: str
    
    class Config:
        from_attributes = True


class StockPriceInfo(BaseModel):
    """Stock with latest price information"""
    ticker: str
    company_name: str
    latest_price: Optional[float]
    price_timestamp: Optional[str]


@router.get("", response_model=List[StockInfo])
async def list_all_stocks(
    db: Annotated[Session, Depends(get_db)]
) -> List[StockInfo]:
    """
    Get list of all stocks in the database.
    """
    try:
        stocks = db.query(Stock).order_by(Stock.ticker).all()
        return [StockInfo(ticker=stock.ticker, company_name=stock.company_name) for stock in stocks]
    except Exception as e:
        logger.error(f"Error fetching stocks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stocks: {str(e)}"
        )


@router.get("/{ticker}/price", response_model=StockPriceInfo)
async def get_stock_price(
    ticker: str,
    db: Annotated[Session, Depends(get_db)]
) -> StockPriceInfo:
    """
    Get the current live stock price for a ticker using multi-source rotation.
    Tries: Yahoo Finance -> Alpha Vantage -> Finnhub -> Database fallback
    """
    try:
        # Get stock from database
        stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()
        if not stock:
            raise HTTPException(
                status_code=404,
                detail=f"Ticker {ticker} not found"
            )
        
        # Check cache first
        ticker_upper = ticker.upper()
        now = datetime.now()
        
        if ticker_upper in _price_cache:
            cached = _price_cache[ticker_upper]
            cache_age = now - cached["timestamp"]
            
            if cache_age < timedelta(minutes=_cache_ttl_minutes):
                logger.info(
                    f"Using cached price for {ticker}: ${cached['price']} "
                    f"from {cached.get('source', 'unknown')} (age: {cache_age.seconds}s)"
                )
                return StockPriceInfo(
                    ticker=stock.ticker,
                    company_name=stock.company_name,
                    latest_price=cached["price"],
                    price_timestamp=None
                )
        
        # Try to fetch live price from multiple sources
        price_service = get_stock_price_service()
        result = price_service.get_live_price(ticker_upper)
        
        if result:
            # Cache the result
            _price_cache[ticker_upper] = {
                "price": result["price"],
                "timestamp": result["timestamp"],
                "source": result["source"]
            }
            
            logger.info(
                f"Fetched and cached price for {ticker}: ${result['price']:.2f} "
                f"from {result['source']}"
            )
            
            return StockPriceInfo(
                ticker=stock.ticker,
                company_name=stock.company_name,
                latest_price=result["price"],
                price_timestamp=None
            )
        
        # All live sources failed, fall back to database
        logger.warning(f"All live sources failed for {ticker}, using database fallback")
        
        latest_record = db.query(HistoricalPremiumRecord).filter(
            HistoricalPremiumRecord.stock_id == stock.stock_id
        ).order_by(
            HistoricalPremiumRecord.collection_timestamp.desc()
        ).first()
        
        if latest_record:
            logger.info(f"Using database price for {ticker}: ${latest_record.stock_price_at_collection}")
            return StockPriceInfo(
                ticker=stock.ticker,
                company_name=stock.company_name,
                latest_price=float(latest_record.stock_price_at_collection),
                price_timestamp=latest_record.collection_timestamp.isoformat()
            )
        else:
            # No price data available at all
            logger.warning(f"No price data available for {ticker}")
            return StockPriceInfo(
                ticker=stock.ticker,
                company_name=stock.company_name,
                latest_price=None,
                price_timestamp=None
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock price: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stock price: {str(e)}"
        )
