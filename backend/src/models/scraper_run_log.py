"""
Scraper Run Log Models

Stores history of scraper runs and individual stock scraping results.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..database.connection import Base


class RunStatus(enum.Enum):
    """Status of a scraper run"""
    running = "running"
    completed = "completed"
    failed = "failed"


class StockScrapeStatus(enum.Enum):
    """Status of individual stock scraping"""
    success = "success"
    failed = "failed"


class ScraperRun(Base):
    """Record of a complete scraper run"""
    __tablename__ = "scraper_runs"

    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(SQLEnum(RunStatus), nullable=False, default=RunStatus.running)
    total_stocks = Column(Integer, nullable=False, default=0)
    successful_stocks = Column(Integer, nullable=False, default=0)
    failed_stocks = Column(Integer, nullable=False, default=0)
    total_contracts = Column(Integer, nullable=False, default=0)
    
    # Relationship to stock logs
    stock_logs = relationship("ScraperStockLog", back_populates="run", cascade="all, delete-orphan")


class ScraperStockLog(Base):
    """Record of scraping a single stock within a run"""
    __tablename__ = "scraper_stock_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("scraper_runs.id"), nullable=False)
    ticker = Column(String(10), nullable=False)
    status = Column(SQLEnum(StockScrapeStatus), nullable=False)
    source_used = Column(String(50), nullable=True)  # yahoo_finance, alpha_vantage, finnhub, database
    contracts_scraped = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    
    # Relationship to run
    run = relationship("ScraperRun", back_populates="stock_logs")
