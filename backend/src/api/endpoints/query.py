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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


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
