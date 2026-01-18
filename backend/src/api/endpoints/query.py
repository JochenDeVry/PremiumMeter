"""
Query API Endpoints

Handles premium data queries with strike/duration matching.
Implements User Story 1 API contract per contracts/openapi.yaml.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated, List, Optional
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


class PremiumBoxPlotRequest(BaseModel):
    """Request model for premium vs stock price box plot"""
    ticker: str
    option_type: str
    strike_price: float
    duration_days: int
    duration_tolerance_days: int = 0
    lookback_days: int = 30


class PremiumBoxPlotDataPoint(BaseModel):
    """Single data point for box plot"""
    stock_price: float
    premium: float
    timestamp: str


class PremiumBoxPlotResponse(BaseModel):
    """Response model for premium vs stock price box plot"""
    ticker: str
    option_type: str
    strike_price: float
    duration_days: int
    data_points: List[PremiumBoxPlotDataPoint]
    total_points: int
    stock_price_range: dict
    collection_period: dict


@router.post("/premium-boxplot", response_model=PremiumBoxPlotResponse)
async def query_premium_boxplot(
    request: PremiumBoxPlotRequest,
    db: Annotated[Session, Depends(get_db)]
) -> PremiumBoxPlotResponse:
    """
    Get premium vs stock price data for box plot visualization.
    Returns pairs of (stock_price_at_collection, premium) for the specified contract.
    """
    try:
        # Validate inputs
        validate_ticker(request.ticker)
        validate_option_type(request.option_type)
        validate_positive_number(request.strike_price, "strike_price", max_value=1000000)
        validate_positive_number(request.duration_days, "duration_days", max_value=365)
        
        logger.info(
            f"Premium box plot request: ticker={request.ticker}, "
            f"strike={request.strike_price}, duration={request.duration_days}"
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
        
        # Query all matching records with stock price and premium
        records = db.query(HistoricalPremiumRecord).filter(
            HistoricalPremiumRecord.stock_id == stock.stock_id,
            HistoricalPremiumRecord.option_type == request.option_type,
            HistoricalPremiumRecord.strike_price == request.strike_price,
            HistoricalPremiumRecord.days_to_expiry >= min_dte,
            HistoricalPremiumRecord.days_to_expiry <= max_dte,
            HistoricalPremiumRecord.collection_timestamp >= start_time,
            HistoricalPremiumRecord.collection_timestamp <= end_time
        ).all()
        
        logger.info(f"Found {len(records)} records for box plot")
        
        # Extract data points
        data_points = [
            PremiumBoxPlotDataPoint(
                stock_price=float(r.stock_price_at_collection),
                premium=float(r.premium),
                timestamp=r.collection_timestamp.isoformat()
            )
            for r in records
        ]
        
        # Calculate stock price range
        if data_points:
            stock_prices = [dp.stock_price for dp in data_points]
            stock_price_range = {
                "min": min(stock_prices),
                "max": max(stock_prices),
                "mean": sum(stock_prices) / len(stock_prices)
            }
            
            timestamps = [r.collection_timestamp for r in records]
            collection_period = {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat()
            }
        else:
            stock_price_range = {"min": 0, "max": 0, "mean": 0}
            collection_period = {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        
        logger.info(
            f"Box plot data: ticker={request.ticker}, points={len(data_points)}, "
            f"stock_price_range={stock_price_range['min']:.2f}-{stock_price_range['max']:.2f}"
        )
        
        return PremiumBoxPlotResponse(
            ticker=request.ticker.upper(),
            option_type=request.option_type,
            strike_price=request.strike_price,
            duration_days=request.duration_days,
            data_points=data_points,
            total_points=len(data_points),
            stock_price_range=stock_price_range,
            collection_period=collection_period
        )
    
    except ValueError as e:
        logger.warning(f"Box plot query validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error in query_premium_boxplot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class PremiumSurfaceRequest(BaseModel):
    """Request model for 3D premium surface plot"""
    ticker: str
    option_type: str
    duration_days: int
    duration_tolerance_days: int = 3
    lookback_days: int = 30


class PremiumSurfaceResponse(BaseModel):
    """Response model for 3D premium surface plot"""
    ticker: str
    option_type: str
    duration_days: int
    strike_prices: List[float]
    stock_prices: List[float]
    premium_grid: List[List[Optional[float]]]  # 2D grid: premium_grid[stock_price_idx][strike_price_idx]
    data_point_counts: List[List[int]]  # Count of data points for each cell
    total_points: int
    collection_period: dict


@router.post("/premium-surface", response_model=PremiumSurfaceResponse)
async def query_premium_surface(
    request: PremiumSurfaceRequest,
    db: Annotated[Session, Depends(get_db)]
) -> PremiumSurfaceResponse:
    """
    Get premium surface data for 3D visualization.
    Returns a grid of premiums across strike prices and stock prices.
    """
    try:
        # Validate inputs
        validate_ticker(request.ticker)
        validate_option_type(request.option_type)
        validate_positive_number(request.duration_days, "duration_days", max_value=365)
        
        logger.info(
            f"Premium surface request: ticker={request.ticker}, "
            f"option_type={request.option_type}, duration={request.duration_days}"
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
            HistoricalPremiumRecord.days_to_expiry >= min_dte,
            HistoricalPremiumRecord.days_to_expiry <= max_dte,
            HistoricalPremiumRecord.collection_timestamp >= start_time,
            HistoricalPremiumRecord.collection_timestamp <= end_time
        ).all()
        
        if not records:
            logger.warning(f"No data found for surface plot: {request.ticker}")
            return PremiumSurfaceResponse(
                ticker=request.ticker.upper(),
                option_type=request.option_type,
                duration_days=request.duration_days,
                strike_prices=[],
                stock_prices=[],
                premium_grid=[],
                data_point_counts=[],
                total_points=0,
                collection_period={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            )
        
        logger.info(f"Found {len(records)} records for surface plot")
        
        # Extract unique strike prices and stock prices
        strike_prices = sorted(list(set(r.strike_price for r in records)))
        stock_prices = sorted(list(set(r.stock_price_at_collection for r in records)))
        
        logger.info(f"Surface dimensions: {len(strike_prices)} strikes × {len(stock_prices)} stock prices")
        
        # Create grid mapping
        strike_to_idx = {price: idx for idx, price in enumerate(strike_prices)}
        stock_to_idx = {price: idx for idx, price in enumerate(stock_prices)}
        
        # Initialize grids
        premium_grid = [[[] for _ in strike_prices] for _ in stock_prices]
        
        # Fill grid with data points
        for record in records:
            stock_idx = stock_to_idx[record.stock_price_at_collection]
            strike_idx = strike_to_idx[record.strike_price]
            premium_grid[stock_idx][strike_idx].append(float(record.premium))
        
        # Calculate average premium for each cell
        avg_premium_grid = []
        count_grid = []
        
        for stock_idx in range(len(stock_prices)):
            avg_row = []
            count_row = []
            for strike_idx in range(len(strike_prices)):
                premiums = premium_grid[stock_idx][strike_idx]
                if premiums:
                    avg_row.append(sum(premiums) / len(premiums))
                    count_row.append(len(premiums))
                else:
                    avg_row.append(None)  # No data for this cell
                    count_row.append(0)
            avg_premium_grid.append(avg_row)
            count_grid.append(count_row)
        
        # Get collection period
        timestamps = [r.collection_timestamp for r in records]
        collection_period = {
            "start": min(timestamps).isoformat(),
            "end": max(timestamps).isoformat()
        }
        
        logger.info(
            f"Surface plot data prepared: {len(records)} total points, "
            f"grid size {len(stock_prices)}×{len(strike_prices)}"
        )
        
        return PremiumSurfaceResponse(
            ticker=request.ticker.upper(),
            option_type=request.option_type,
            duration_days=request.duration_days,
            strike_prices=[float(p) for p in strike_prices],
            stock_prices=[float(p) for p in stock_prices],
            premium_grid=avg_premium_grid,
            data_point_counts=count_grid,
            total_points=len(records),
            collection_period=collection_period
        )
    
    except ValueError as e:
        logger.warning(f"Surface plot query validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error in query_premium_surface: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
