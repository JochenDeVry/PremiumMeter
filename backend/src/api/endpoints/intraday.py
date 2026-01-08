"""
Intraday Stock Price API Endpoints

Provides intraday stock price data for chart visualization.
Uses Alpha Vantage and Finnhub to offload Yahoo Finance.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Annotated, List, Dict, Optional
import logging
from datetime import datetime, timedelta
from alpha_vantage.timeseries import TimeSeries
import finnhub
import pandas as pd
import os
import yfinance as yf

from ...database.connection import get_db
from ...models.stock import Stock
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intraday", tags=["intraday"])


class IntradayDataPoint(BaseModel):
    """Single intraday price point"""
    timestamp: str
    price: float
    volume: Optional[int] = None


class IntradayResponse(BaseModel):
    """Response with intraday price data"""
    ticker: str
    company_name: str
    data_points: List[IntradayDataPoint]
    source: str
    date: str  # Trading date (YYYY-MM-DD)


def fetch_alpha_vantage_intraday(ticker: str) -> Optional[IntradayResponse]:
    """Fetch intraday data from Alpha Vantage (5-minute intervals)"""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.warning("Alpha Vantage API key not configured")
        return None
    
    try:
        ts = TimeSeries(key=api_key, output_format='json')
        data, meta_data = ts.get_intraday(symbol=ticker.upper(), interval='5min', outputsize='compact')
        
        # Check for API error messages (rate limit, invalid symbol, etc.)
        if isinstance(data, dict):
            # Check for common error keys
            if 'Error Message' in data:
                logger.error(f"Alpha Vantage error: {data['Error Message']}")
                return None
            if 'Note' in data:
                logger.warning(f"Alpha Vantage note: {data['Note']}")
                return None
            if 'Information' in data:
                logger.warning(f"Alpha Vantage info: {data['Information']}")
                return None
        
        # Alpha Vantage returns dict with timestamps as keys
        # Format: {'2024-01-07 15:55:00': {'1. open': '180.50', '2. high': '180.60', ...}}
        data_points = []
        
        # Get today's date to filter only today's data
        today = datetime.now().date()
        
        for timestamp_str, values in sorted(data.items()):
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                
                # Only include today's data
                if timestamp.date() != today:
                    continue
                
                data_points.append(IntradayDataPoint(
                    timestamp=timestamp.isoformat(),
                    price=float(values['4. close']),
                    volume=int(values['5. volume'])
                ))
            except (ValueError, KeyError) as e:
                # Skip invalid entries
                logger.debug(f"Skipping invalid data point: {e}")
                continue
        
        if data_points:
            return IntradayResponse(
                ticker=ticker.upper(),
                company_name="",  # Will be filled from database
                data_points=data_points,
                source="Alpha Vantage",
                date=today.isoformat()
            )
        
        logger.info(f"No intraday data points found for {ticker} from Alpha Vantage")
        return None
        
        return None
        
    except Exception as e:
        logger.error(f"Alpha Vantage intraday error for {ticker}: {e}")
        return None


def fetch_finnhub_intraday(ticker: str) -> Optional[IntradayResponse]:
    """Fetch intraday data from Finnhub (1-minute resolution)"""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        logger.warning("Finnhub API key not configured")
        return None
    
    try:
        client = finnhub.Client(api_key=api_key)
        
        # Get today's candles (1-minute resolution)
        today = datetime.now().date()
        
        # Market opens at 9:30 AM ET
        start_of_day = datetime.combine(today, datetime.min.time())
        start_timestamp = int(start_of_day.timestamp())
        end_timestamp = int(datetime.now().timestamp())
        
        # Get candles with 5-minute resolution
        res = client.stock_candles(ticker.upper(), '5', start_timestamp, end_timestamp)
        
        if res and 's' in res and res['s'] == 'ok':
            data_points = []
            
            for i in range(len(res['t'])):
                timestamp = datetime.fromtimestamp(res['t'][i])
                data_points.append(IntradayDataPoint(
                    timestamp=timestamp.isoformat(),
                    price=float(res['c'][i]),  # Close price
                    volume=int(res['v'][i])
                ))
            
            if data_points:
                return IntradayResponse(
                    ticker=ticker.upper(),
                    company_name="",
                    data_points=data_points,
                    source="Finnhub",
                    date=today.isoformat()
                )
        
        return None
        
    except Exception as e:
        logger.error(f"Finnhub intraday error for {ticker}: {e}")
        return None


def fetch_yfinance_intraday(ticker: str) -> Optional[IntradayResponse]:
    """Fetch intraday data from Yahoo Finance (5-minute intervals) as fallback"""
    try:
        yf_ticker = yf.Ticker(ticker.upper())
        
        # Get today's intraday data with 5-minute intervals
        hist = yf_ticker.history(period='1d', interval='5m')
        
        if hist.empty:
            logger.info(f"No intraday data from Yahoo Finance for {ticker}")
            return None
        
        data_points = []
        today = datetime.now().date()
        
        for timestamp, row in hist.iterrows():
            # Convert pandas Timestamp to datetime
            dt = timestamp.to_pydatetime()
            
            # Only include today's data
            if dt.date() != today:
                continue
            
            data_points.append(IntradayDataPoint(
                timestamp=dt.isoformat(),
                price=float(row['Close']),
                volume=int(row['Volume']) if 'Volume' in row and not pd.isna(row['Volume']) else None
            ))
        
        if data_points:
            return IntradayResponse(
                ticker=ticker.upper(),
                company_name="",
                data_points=data_points,
                source="Yahoo Finance",
                date=today.isoformat()
            )
        
        logger.info(f"No intraday data points found for {ticker} from Yahoo Finance")
        return None
        
    except Exception as e:
        logger.error(f"Yahoo Finance intraday error for {ticker}: {e}")
        return None


@router.get("/{ticker}", response_model=IntradayResponse)
async def get_intraday_prices(
    ticker: str,
    db: Annotated[Session, Depends(get_db)]
) -> IntradayResponse:
    """
    Get intraday stock price data for the current trading day.
    
    Uses Alpha Vantage or Finnhub (not Yahoo Finance) to reduce load.
    Returns 5-minute interval data for the current day.
    """
    try:
        # Verify stock exists in database
        stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()
        if not stock:
            raise HTTPException(
                status_code=404,
                detail=f"Ticker {ticker} not found in database"
            )
        
        # Check if API keys are configured
        alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        finnhub_key = os.getenv("FINNHUB_API_KEY")
        
        # Try Alpha Vantage first (if available)
        if alpha_vantage_key:
            logger.info(f"Fetching intraday data for {ticker} from Alpha Vantage")
            result = fetch_alpha_vantage_intraday(ticker)
            
            if result:
                result.company_name = stock.company_name
                logger.info(f"Retrieved {len(result.data_points)} intraday points for {ticker} from Alpha Vantage")
                return result
            else:
                logger.warning(f"Alpha Vantage returned no data for {ticker}")
        
        # Fallback to Finnhub
        if finnhub_key:
            logger.info(f"Trying Finnhub for {ticker}")
            result = fetch_finnhub_intraday(ticker)
            
            if result:
                result.company_name = stock.company_name
                logger.info(f"Retrieved {len(result.data_points)} intraday points for {ticker} from Finnhub")
                return result
            else:
                logger.warning(f"Finnhub returned no data for {ticker}")
        
        # Final fallback to Yahoo Finance (always available, no API key needed)
        logger.info(f"Trying Yahoo Finance for {ticker}")
        result = fetch_yfinance_intraday(ticker)
        
        if result:
            result.company_name = stock.company_name
            logger.info(f"Retrieved {len(result.data_points)} intraday points for {ticker} from Yahoo Finance")
            return result
        
        # No data available from any source
        logger.error(f"All intraday data sources failed for {ticker}")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch intraday data for {ticker}. This could be due to: (1) Market is closed, (2) No data available for today, or (3) API service issues."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching intraday data for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve intraday data: {str(e)}"
        )
