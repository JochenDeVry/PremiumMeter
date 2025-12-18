"""
Historical Premium Record model - Time-series data for options premiums
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, ForeignKey, Index, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from src.database.connection import Base


class OptionType(str, enum.Enum):
    """Option type enumeration"""
    call = "call"
    put = "put"


class ContractStatus(str, enum.Enum):
    """Contract status enumeration"""
    active = "active"
    expired = "expired"


class HistoricalPremiumRecord(Base):
    """
    Historical Premium Record entity - Time-series data for options premiums
    
    Corresponds to spec.md Key Entities: Historical Premium Record
    Supports intra-day polling design (5-minute intervals during market hours)
    """
    __tablename__ = "historical_premium_records"

    # Primary Key
    record_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    stock_id = Column(Integer, ForeignKey('stock.stock_id', ondelete='CASCADE'), nullable=False)
    
    # Options Contract Information
    option_type = Column(Enum(OptionType, name="option_type"), nullable=False)
    strike_price = Column(Numeric(10, 2), nullable=False)
    expiration_date = Column(Date, nullable=False)
    
    # Premium Data
    premium = Column(Numeric(10, 2), nullable=False)
    
    # Stock Price at Collection (for moneyness analysis)
    stock_price_at_collection = Column(Numeric(10, 2), nullable=False)
    
    # Greeks (calculated or from data source)
    implied_volatility = Column(Numeric(6, 4))
    delta = Column(Numeric(6, 4))
    gamma = Column(Numeric(6, 4))
    theta = Column(Numeric(6, 4))
    vega = Column(Numeric(6, 4))
    rho = Column(Numeric(6, 4))
    
    # Volume and Open Interest
    volume = Column(Integer)
    open_interest = Column(Integer)
    
    # Contract Metadata
    contract_status = Column(
        Enum(ContractStatus, name="contract_status"),
        default=ContractStatus.active,
        nullable=False
    )
    days_to_expiry = Column(Integer, nullable=False)
    
    # Scraper Metadata
    data_source = Column(String(50), default='yahoo_finance')
    scraper_run_id = Column(String(50))
    
    # Timestamps
    collection_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Relationship
    stock = relationship("Stock", backref="premium_records")
    
    # Indexes for query performance (per data-model.md)
    __table_args__ = (
        # Primary query pattern: ticker + option_type + strike + duration + time_range
        Index('idx_premium_query_main', 'stock_id', 'option_type', 'strike_price', 'days_to_expiry', 'collection_timestamp'),
        
        # Time-series queries
        Index('idx_premium_collection_time', 'collection_timestamp'),
        Index('idx_premium_stock_time', 'stock_id', 'collection_timestamp'),
        
        # Strike price range queries
        Index('idx_premium_strike_range', 'stock_id', 'option_type', 'strike_price'),
        
        # Expiration queries
        Index('idx_premium_expiration', 'expiration_date', 'contract_status'),
        
        # Will be converted to TimescaleDB hypertable partitioned by collection_timestamp
    )
    
    def __repr__(self):
        return (
            f"<HistoricalPremiumRecord("
            f"stock_id={self.stock_id}, "
            f"type={self.option_type.value}, "
            f"strike=${self.strike_price}, "
            f"premium=${self.premium}, "
            f"expiry={self.days_to_expiry}d"
            f")>"
        )
