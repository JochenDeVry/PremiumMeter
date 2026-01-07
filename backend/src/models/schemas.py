"""
Pydantic schemas for request/response validation.
Provides type-safe API contracts and data validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum

# Base configuration for all schemas
class BaseSchema(BaseModel):
    """Base Pydantic model with common configuration"""
    
    class Config:
        from_attributes = True  # Enable ORM mode (Pydantic v2)
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

# Enums
class OptionType(str, Enum):
    """Option type enum"""
    call = "call"
    put = "put"

class StrikeModeType(str, Enum):
    """Strike price matching mode"""
    exact = "exact"
    percentage_range = "percentage_range"
    nearest = "nearest"

class ContractStatus(str, Enum):
    """Contract status enum"""
    active = "active"
    expired = "expired"

class MonitoringStatus(str, Enum):
    """Watchlist monitoring status"""
    active = "active"
    paused = "paused"

class SchedulerStatus(str, Enum):
    """Scheduler status enum"""
    idle = "idle"
    running = "running"
    paused = "paused"
    error = "error"


# ============================================================================
# User Story 1: Query Premium Data Schemas
# ============================================================================

class PremiumQueryRequest(BaseSchema):
    """
    Request schema for querying historical premium data.
    
    Supports three strike matching modes:
    1. exact: Match specific strike price
    2. percentage_range: Match strikes within percentage range
    3. nearest: Match N nearest strikes above/below target
    """
    ticker: str = Field(..., description="Stock ticker symbol", min_length=1, max_length=10)
    option_type: OptionType = Field(..., description="Option type: call or put")
    
    # Strike matching configuration
    strike_mode: StrikeModeType = Field(
        default=StrikeModeType.exact,
        description="How to match strike prices"
    )
    strike_price: Optional[Decimal] = Field(
        None,
        description="Target strike price (required for exact and percentage_range modes)",
        gt=0
    )
    strike_range_percent: Optional[float] = Field(
        None,
        description="Percentage range for strike matching (percentage_range mode only)",
        ge=0,
        le=100
    )
    nearest_count_above: Optional[int] = Field(
        None,
        description="Number of strikes above current price (nearest mode only)",
        ge=1,
        le=50
    )
    nearest_count_below: Optional[int] = Field(
        None,
        description="Number of strikes below current price (nearest mode only)",
        ge=1,
        le=50
    )
    
    # Duration matching
    duration_days: Optional[int] = Field(
        None,
        description="Target days to expiration",
        ge=0
    )
    duration_tolerance_days: Optional[int] = Field(
        default=3,
        description="Tolerance in days for duration matching",
        ge=0
    )
    
    # Time range
    lookback_days: Optional[int] = Field(
        default=30,
        description="How many days back to query (use large value like 3650 for entire database)",
        ge=1,
        le=3650
    )
    
    @field_validator('strike_price')
    @classmethod
    def validate_strike_price(cls, v, info):
        """Ensure strike_price is provided for exact and percentage_range modes"""
        strike_mode = info.data.get('strike_mode')
        if strike_mode in (StrikeModeType.exact, StrikeModeType.percentage_range) and v is None:
            raise ValueError(f"strike_price is required for {strike_mode.value} mode")
        return v
    
    @field_validator('strike_range_percent')
    @classmethod
    def validate_strike_range(cls, v, info):
        """Ensure strike_range_percent is provided for percentage_range mode"""
        strike_mode = info.data.get('strike_mode')
        if strike_mode == StrikeModeType.percentage_range and v is None:
            raise ValueError("strike_range_percent is required for percentage_range mode")
        return v
    
    @field_validator('nearest_count_above')
    @classmethod
    def validate_nearest_counts(cls, v, info):
        """Ensure at least one nearest count is provided for nearest mode"""
        strike_mode = info.data.get('strike_mode')
        nearest_below = info.data.get('nearest_count_below')
        if strike_mode == StrikeModeType.nearest and v is None and nearest_below is None:
            raise ValueError("At least one of nearest_count_above or nearest_count_below is required for nearest mode")
        return v


class PremiumStatistics(BaseSchema):
    """Statistical summary for a specific strike price"""
    strike_price: Decimal = Field(..., description="Strike price")
    duration_days: int = Field(..., description="Duration in days to expiry")
    
    # Premium statistics
    min_premium: Decimal = Field(..., description="Minimum premium observed")
    max_premium: Decimal = Field(..., description="Maximum premium observed")
    avg_premium: Decimal = Field(..., description="Average premium")
    median_premium: Optional[Decimal] = Field(None, description="Median premium")
    std_premium: Optional[Decimal] = Field(None, description="Standard deviation of premium")
    
    # Greeks averages
    avg_delta: Optional[Decimal] = Field(None, description="Average delta")
    avg_gamma: Optional[Decimal] = Field(None, description="Average gamma")
    avg_theta: Optional[Decimal] = Field(None, description="Average theta")
    avg_vega: Optional[Decimal] = Field(None, description="Average vega")
    
    # Data quality metrics
    data_points: int = Field(..., description="Number of data points in this statistic", ge=0)
    first_seen: datetime = Field(..., description="Earliest collection timestamp")
    last_seen: datetime = Field(..., description="Latest collection timestamp")


class PremiumQueryResponse(BaseSchema):
    """Response schema for premium query results"""
    ticker: str = Field(..., description="Stock ticker queried")
    option_type: str = Field(..., description="Option type queried")
    query_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When query was executed")
    current_stock_price: Optional[Decimal] = Field(None, description="Current stock price at query time")
    
    # Query parameters echoed back
    strike_mode: str = Field(..., description="Strike matching mode used")
    duration_days: Optional[int] = Field(None, description="Target duration queried")
    lookback_days: int = Field(..., description="Lookback period used")
    
    # Results
    results: List[PremiumStatistics] = Field(
        default_factory=list,
        description="Premium statistics for each matching strike"
    )
    total_strikes: int = Field(..., description="Number of strikes in results", ge=0)
    total_data_points: int = Field(..., description="Total data points across all strikes", ge=0)


# ============================================================================
# Watchlist Schemas
# ============================================================================

class WatchlistStock(BaseSchema):
    """Stock entry in the watchlist"""
    stock_id: int = Field(..., description="Database ID of the stock")
    ticker: str = Field(..., description="Stock ticker symbol")
    company_name: str = Field(..., description="Company name")
    status: MonitoringStatus = Field(..., description="Monitoring status")
    added_at: str = Field(..., description="When stock was added to watchlist")
    last_scraped: Optional[str] = Field(None, description="Last successful scrape timestamp")
    data_points_count: int = Field(..., description="Number of historical data points", ge=0)


class WatchlistResponse(BaseSchema):
    """Response containing the watchlist"""
    watchlist: List[WatchlistStock] = Field(..., description="List of stocks in watchlist")
    total_count: int = Field(..., description="Total number of stocks", ge=0)


class AddStockRequest(BaseSchema):
    """Request to add a stock to the watchlist"""
    ticker: str = Field(..., description="Stock ticker symbol", min_length=1, max_length=10)
    company_name: Optional[str] = Field(None, description="Company name (optional)")


class RemoveStockRequest(BaseSchema):
    """Request to remove a stock from the watchlist"""
    ticker: str = Field(..., description="Stock ticker symbol", min_length=1, max_length=10)


class UpdateStockStatusRequest(BaseSchema):
    """Request to update stock status (activate/deactivate)"""
    ticker: str = Field(..., description="Stock ticker symbol", min_length=1, max_length=10)
    status: str = Field(..., description="New status (active/inactive)")


class BulkStockActionRequest(BaseSchema):
    """Request to perform bulk action on multiple stocks"""
    tickers: List[str] = Field(..., description="List of stock ticker symbols", min_length=1)
    action: str = Field(..., description="Action to perform: activate, deactivate, or remove")


# ============================================================================
# Scheduler Schemas
# ============================================================================

class SchedulerConfig(BaseSchema):
    """Scheduler configuration"""
    polling_interval_minutes: int = Field(..., description="Polling interval in minutes", ge=1)
    market_hours_start: str = Field(..., description="Market open time (HH:MM format)")
    market_hours_end: str = Field(..., description="Market close time (HH:MM format)")
    timezone: str = Field(..., description="Timezone for market hours")
    exclude_weekends: bool = Field(..., description="Whether to exclude weekends")
    exclude_holidays: bool = Field(..., description="Whether to exclude holidays")
    status: SchedulerStatus = Field(..., description="Scheduler status")
    next_run: Optional[str] = Field(None, description="Next scheduled run time")
    last_run: Optional[str] = Field(None, description="Last run time")
    stock_delay_seconds: int = Field(..., description="Delay between scraping stocks (seconds)", ge=0)
    max_expirations: int = Field(..., description="Maximum number of option expirations per stock", ge=1)


class SchedulerConfigRequest(BaseSchema):
    """Request to update scheduler configuration"""
    polling_interval_minutes: Optional[int] = Field(None, description="Polling interval in minutes", ge=1, le=1440)
    market_hours_start: Optional[str] = Field(None, description="Market open time (HH:MM format)")
    market_hours_end: Optional[str] = Field(None, description="Market close time (HH:MM format)")
    timezone: Optional[str] = Field(None, description="Timezone for market hours")
    exclude_weekends: Optional[bool] = Field(None, description="Whether to exclude weekends")
    exclude_holidays: Optional[bool] = Field(None, description="Whether to exclude holidays")
    stock_delay_seconds: Optional[int] = Field(None, description="Delay between scraping stocks (seconds)", ge=0, le=300)
    max_expirations: Optional[int] = Field(None, description="Maximum number of option expirations per stock", ge=1, le=100)


class ScraperProgress(BaseSchema):
    """Current scraper progress"""
    is_running: bool = Field(..., description="Whether scraper is currently running")
    total_stocks: int = Field(..., description="Total number of stocks to scrape")
    completed_stocks: int = Field(..., description="Number of stocks completed")
    current_stock: Optional[str] = Field(None, description="Currently scraping stock ticker")
    current_source: Optional[str] = Field(None, description="Current data source being used")
    pending_stocks: List[str] = Field(default_factory=list, description="Stocks pending to be scraped")
    completed_stock_list: List[str] = Field(default_factory=list, description="Stocks that have been scraped")
    failed_stocks: List[str] = Field(default_factory=list, description="Stocks that failed")
    start_time: Optional[str] = Field(None, description="Scrape start timestamp")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time")


class RateLimitCalculation(BaseSchema):
    """Rate limit calculation based on current configuration"""
    watchlist_size: int = Field(..., description="Number of active stocks in watchlist")
    requests_per_stock: int = Field(..., description="Estimated API requests per stock")
    requests_per_cycle: int = Field(..., description="Total requests per scrape cycle")
    cycle_duration_minutes: float = Field(..., description="Estimated cycle duration in minutes")
    requests_per_minute: float = Field(..., description="Average requests per minute")
    cycles_per_hour: float = Field(..., description="Number of scrape cycles per hour")
    requests_per_hour: float = Field(..., description="Estimated requests per hour")
    cycles_per_day: int = Field(..., description="Number of scrape cycles per day")
    requests_per_day: int = Field(..., description="Estimated requests per day")
    within_minute_limit: bool = Field(..., description="Whether within 60/min limit")
    within_hour_limit: bool = Field(..., description="Whether within 360/hour limit")
    within_day_limit: bool = Field(..., description="Whether within 8000/day limit")
    warnings: List[str] = Field(default_factory=list, description="Rate limit warnings")


# ============================================================================
# Scraper Run Log Schemas
# ============================================================================

class StockScrapeLogSchema(BaseSchema):
    """Log entry for a single stock scrape"""
    ticker: str = Field(..., description="Stock ticker symbol")
    status: str = Field(..., description="success or failed")
    source_used: Optional[str] = Field(None, description="Data source used")
    contracts_scraped: Optional[int] = Field(None, description="Number of contracts scraped")
    timestamp: str = Field(..., description="Timestamp of scrape")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ScraperRunSchema(BaseSchema):
    """Complete scraper run record"""
    id: int = Field(..., description="Run ID")
    start_time: str = Field(..., description="Run start timestamp")
    end_time: Optional[str] = Field(None, description="Run end timestamp")
    status: str = Field(..., description="running, completed, or failed")
    total_stocks: int = Field(..., description="Total stocks to scrape")
    successful_stocks: int = Field(..., description="Successfully scraped stocks")
    failed_stocks: int = Field(..., description="Failed stock scrapes")
    total_contracts: int = Field(..., description="Total contracts scraped")
    stock_logs: List[StockScrapeLogSchema] = Field(default_factory=list, description="Individual stock logs")


class ScraperRunHistoryResponse(BaseSchema):
    """Response with scraper run history"""
    runs: List[ScraperRunSchema] = Field(..., description="List of scraper runs")
    total_count: int = Field(..., description="Total number of runs")


# ============================================================================
# Common Response Schemas
# ============================================================================

class SuccessResponse(BaseSchema):
    """Generic success response"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Human-readable message")


__all__ = [
    "BaseSchema",
    "OptionType",
    "StrikeModeType",
    "ContractStatus",
    "MonitoringStatus",
    "SchedulerStatus",
    "PremiumQueryRequest",
    "GreeksAverage",
    "PremiumResult",
    "PremiumQueryResponse",
    "WatchlistStock",
    "WatchlistResponse",
    "AddStockRequest",
    "RemoveStockRequest",
    "UpdateStockStatusRequest",
    "BulkStockActionRequest",
    "PremiumQueryRequest",
    "PremiumStatistics",
    "PremiumQueryResponse",
    "WatchlistStock",
    "WatchlistResponse",
    "AddStockRequest",
    "RemoveStockRequest",
    "SchedulerConfig",
    "SchedulerConfigRequest",
    "ScraperProgress",
    "RateLimitCalculation",
    "StockScrapeLogSchema",
    "ScraperRunSchema",
    "ScraperRunHistoryResponse",
    "SuccessResponse"
]
