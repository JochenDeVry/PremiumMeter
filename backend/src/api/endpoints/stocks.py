"""
Stocks API Endpoints

Handles stock information retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated, List
import logging

from ...database.connection import get_db
from ...models.stock import Stock
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


class StockInfo(BaseModel):
    """Basic stock information"""
    ticker: str
    company_name: str
    
    class Config:
        from_attributes = True


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
