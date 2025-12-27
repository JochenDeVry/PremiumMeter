"""
Query API Endpoints

Handles premium data queries with strike/duration matching.
Implements User Story 1 API contract per contracts/openapi.yaml.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
import logging

from ...database.connection import get_db
from ...models.schemas import PremiumQueryRequest, PremiumQueryResponse
from ...services.query_service import QueryService
from ...utils.security import validate_ticker, validate_positive_number, validate_option_type
from ...models.historical_premium_record import HistoricalPremiumRecord
from ...models.stock import Stock
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


class PremiumDistributionRequest(BaseModel):
    """Request for premium distribution data (histogram)"""
    ticker: str
    option_type: str
    strike_price: float
    duration_days: int
    duration_tolerance_days: int = 3
    lookback_days: int = 30


class PremiumDistributionResponse(BaseModel):
    """Response with raw premium values for histogram generation"""
    ticker: str
    option_type: str
    strike_price: float
    duration_days: int
    premiums: list[float]
    data_points: int
    collection_period: dict


@router.post("/premium", response_model=PremiumQueryResponse)
async def query_premium(
    request: PremiumQueryRequest,
    db: Annotated[Session, Depends(get_db)]
) -> PremiumQueryResponse:
    """
    Query historical premium statistics for options contracts.
    
    Supports three strike matching modes:
    - exact: Match specific strike price
    - percentage_range: Match strikes within percentage range of target
    - nearest: Match N nearest strikes above/below current stock price
    
    Duration matching uses days_to_expiry with configurable tolerance.
    Lookback window filters data collection timestamp.
    
    Returns aggregated statistics (min/max/avg premium, Greeks) for each matching strike.
    
    **Example Request:**
    ```json
    {
        "ticker": "META",
        "option_type": "put",
        "strike_mode": "exact",
        "strike_price": 635.00,
        "duration_days": 14,
        "lookback_days": 30
    }
    ```
    
    **Response:**
    Returns statistics with data_points count indicating sample size.
    If no data found, returns empty results array (not 404).
    
    **Errors:**
    - 400: Invalid request (validation errors, unknown ticker)
    - 500: Internal server error
    """
    try:
        # Security validations
        validate_ticker(request.ticker)
        validate_option_type(request.option_type.value)
        
        if request.strike_price:
            validate_positive_number(request.strike_price, "strike_price", max_value=1000000)
        
        if request.duration_days:
            validate_positive_number(request.duration_days, "duration_days", max_value=365)
        
        query_service = QueryService(db)
        response = query_service.query_premium_statistics(request)
        
        # Log query for analytics
        logger.info(
            f"Premium query: ticker={request.ticker}, type={request.option_type.value}, "
            f"mode={request.strike_mode.value}, strikes={response.total_strikes}, "
            f"points={response.total_data_points}"
        )
        
        return response
    
    except ValueError as e:
        # Handle business logic errors (ticker not found, invalid parameters)
        logger.warning(f"Query validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Catch unexpected errors - log full traceback
        logger.error(f"Unexpected error in query_premium: {e}", exc_info=True)
        logger.error(f"Request was: {request.dict()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/premium-distribution", response_model=PremiumDistributionResponse)
async def query_premium_distribution(
    request: PremiumDistributionRequest,
    db: Annotated[Session, Depends(get_db)]
) -> PremiumDistributionResponse:
    """
    Query raw premium values for histogram generation.
    
    Returns all individual premium data points for a specific strike/duration combination
    to allow visualization of premium distribution and probability analysis.
    
    **Example Request:**
    ```json
    {
        "ticker": "AAPL",
        "option_type": "call",
        "strike_price": 150.0,
        "duration_days": 30,
        "duration_tolerance_days": 3,
        "lookback_days": 30
    }
    ```
    
    **Response:**
    Returns array of premium values that can be used to generate histogram showing
    the frequency distribution and probability of specific premium levels.
    """
    try:
        # Security validations
        validate_ticker(request.ticker)
        validate_option_type(request.option_type)
        validate_positive_number(request.strike_price, "strike_price", max_value=1000000)
        validate_positive_number(request.duration_days, "duration_days", max_value=365)
        
        # Log the incoming request for debugging
        logger.info(
            f"Premium distribution request: ticker={request.ticker}, "
            f"strike={request.strike_price}, duration={request.duration_days}, "
            f"tolerance={request.duration_tolerance_days}, lookback={request.lookback_days}"
        )
        
        # Get stock
        stock = db.query(Stock).filter(Stock.ticker == request.ticker.upper()).first()
        if not stock:
            raise ValueError(f"Ticker {request.ticker} not found")
        
        # Calculate time window
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=request.lookback_days)
        
        # Calculate duration range
        min_dte = request.duration_days - request.duration_tolerance_days
        max_dte = request.duration_days + request.duration_tolerance_days
        
        # Query all matching records
        records = db.query(HistoricalPremiumRecord).filter(
            HistoricalPremiumRecord.stock_id == stock.stock_id,
            HistoricalPremiumRecord.option_type == request.option_type,
            HistoricalPremiumRecord.strike_price == request.strike_price,
            HistoricalPremiumRecord.days_to_expiry >= min_dte,
            HistoricalPremiumRecord.days_to_expiry <= max_dte,
            HistoricalPremiumRecord.collection_timestamp >= start_time,
            HistoricalPremiumRecord.collection_timestamp <= end_time
        ).all()
        
        # Log detailed info for debugging
        logger.info(
            f"Distribution query filters: strike={request.strike_price}, "
            f"dte_range={min_dte}-{max_dte}, time_range={start_time.isoformat()[:19]}-{end_time.isoformat()[:19]}"
        )
        logger.info(f"Found {len(records)} records")
        
        # Extract premium values
        premiums = [float(r.premium) for r in records]
        
        # Get collection period from actual data
        if records:
            timestamps = [r.collection_timestamp for r in records]
            collection_period = {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat()
            }
        else:
            collection_period = {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        
        logger.info(
            f"Premium distribution query: ticker={request.ticker}, "
            f"strike={request.strike_price}, data_points={len(premiums)}"
        )
        
        return PremiumDistributionResponse(
            ticker=request.ticker.upper(),
            option_type=request.option_type,
            strike_price=request.strike_price,
            duration_days=request.duration_days,
            premiums=premiums,
            data_points=len(premiums),
            collection_period=collection_period
        )
    
    except ValueError as e:
        logger.warning(f"Distribution query validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error in query_premium_distribution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
