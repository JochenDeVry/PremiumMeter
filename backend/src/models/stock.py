"""
Stock model - Represents stocks in the system
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, Index
from sqlalchemy.sql import func
from datetime import datetime
import enum

from src.database.connection import Base


class StockStatus(str, enum.Enum):
    """Stock status enumeration"""
    ACTIVE = "active"
    DELISTED = "delisted"
    INACTIVE = "inactive"


class Stock(Base):
    """
    Stock entity - represents stocks tracked in the system
    
    Corresponds to spec.md Key Entities: Stock
    """
    __tablename__ = "stocks"

    # Primary Key
    stock_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Stock Information
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    status = Column(
        Enum(StockStatus, name="stock_status"),
        default=StockStatus.ACTIVE,
        nullable=False
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_stocks_ticker', 'ticker'),
        Index('idx_stocks_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Stock(ticker='{self.ticker}', company_name='{self.company_name}', status='{self.status.value}')>"
