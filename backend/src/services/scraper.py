"""
Yahoo Finance Options Scraper Service

Scrapes options chain data from Yahoo Finance using yfinance library.
Implements error handling, retry logic, and concurrency protection.

References:
- research.md: yfinance integration approach, scraper architecture
- data-model.md: HistoricalPremiumRecord schema
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import time

from ..models.stock import Stock, StockStatus
from ..models.historical_premium_record import HistoricalPremiumRecord, OptionType, ContractStatus
from ..models.watchlist import Watchlist, MonitoringStatus
from ..models.scraper_schedule import ScraperSchedule
from .greeks import get_greeks_calculator
from ..config import settings

logger = logging.getLogger(__name__)


class ScraperMetrics:
    """Metrics for a single scraper run"""
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_stocks: int = 0
        self.successful_stocks: int = 0
        self.failed_stocks: int = 0
        self.total_contracts: int = 0
        self.stock_errors: List[Dict[str, str]] = []  # [{ticker, error}]
        self.total_api_requests: int = 0  # Track Yahoo Finance API calls
        self.rate_limit_warnings: List[str] = []  # Rate limit violation warnings
    
    def duration_seconds(self) -> Optional[float]:
        """Calculate scraper run duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for logging"""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds(),
            'total_stocks': self.total_stocks,
            'successful_stocks': self.successful_stocks,
            'failed_stocks': self.failed_stocks,
            'total_contracts': self.total_contracts,
            'contracts_per_stock': round(self.total_contracts / self.successful_stocks, 2) if self.successful_stocks > 0 else 0,
            'total_api_requests': self.total_api_requests,
            'requests_per_stock': round(self.total_api_requests / self.successful_stocks, 2) if self.successful_stocks > 0 else 0,
            'rate_limit_warnings': self.rate_limit_warnings,
            'errors': self.stock_errors
        }


class YahooFinanceScraper:
    """
    Scrapes options chain data from Yahoo Finance.
    
    Fetches all available option contracts (calls and puts) for stocks in the watchlist,
    calculates Greeks using Black-Scholes model, and stores in HistoricalPremiumRecord.
    """
    
    def __init__(self, db: Session):
        """
        Initialize scraper with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.greeks_calculator = get_greeks_calculator(settings.risk_free_rate)
        self.run_id = datetime.now().strftime('%Y%m%d_%H%M%S')  # Unique ID for this run
    
    def scrape_all_stocks(self) -> ScraperMetrics:
        """
        Scrape options data for all active stocks in watchlist.
        
        Returns:
            ScraperMetrics with execution statistics
        """
        from ..services.scheduler import update_scraper_progress
        from datetime import timedelta
        from ..models.scraper_run_log import ScraperRun, ScraperStockLog, RunStatus, StockScrapeStatus
        
        metrics = ScraperMetrics()
        metrics.start_time = datetime.now()
        
        logger.info(f"Starting scraper run: {self.run_id}")
        
        # Create scraper run record
        scraper_run = ScraperRun(
            start_time=metrics.start_time,
            status=RunStatus.running
        )
        self.db.add(scraper_run)
        self.db.commit()
        self.db.refresh(scraper_run)
        
        # Get active watchlist stocks
        active_stocks = self._get_active_watchlist()
        metrics.total_stocks = len(active_stocks)
        
        # Update run record with total stocks
        scraper_run.total_stocks = metrics.total_stocks
        self.db.commit()
        
        logger.info(f"Found {metrics.total_stocks} active stocks in watchlist")
        
        # Load scraper configuration from database
        from ..models.scraper_schedule import ScraperSchedule
        config = self.db.query(ScraperSchedule).first()
        stock_delay = config.stock_delay_seconds if config else 10
        
        # Initialize progress tracking
        pending_tickers = [s.ticker for s in active_stocks]
        update_scraper_progress(
            is_running=True,
            total_stocks=metrics.total_stocks,
            completed_stocks=0,
            current_stock=None,
            pending_stocks=pending_tickers,
            completed_stock_list=[],
            failed_stocks=[],
            start_time=metrics.start_time.isoformat(),
            estimated_completion=(metrics.start_time + timedelta(seconds=metrics.total_stocks * stock_delay * 1.5)).isoformat()
        )
        
        completed_list = []
        failed_list = []
        
        for idx, stock in enumerate(active_stocks):
            stock_log_entry = None
            try:
                # Update current stock being scraped
                update_scraper_progress(
                    current_stock=stock.ticker,
                    pending_stocks=[s.ticker for s in active_stocks[idx+1:]]
                )
                
                # Add delay between stocks to avoid rate limiting
                time.sleep(stock_delay)
                
                contracts_count, api_calls, source_used = self._scrape_stock(stock)
                metrics.total_api_requests += api_calls
                metrics.successful_stocks += 1
                metrics.total_contracts += contracts_count
                completed_list.append(stock.ticker)
                
                # Log successful stock scrape
                stock_log_entry = ScraperStockLog(
                    run_id=scraper_run.id,
                    ticker=stock.ticker,
                    status=StockScrapeStatus.success,
                    source_used=source_used,
                    contracts_scraped=contracts_count,
                    timestamp=datetime.now()
                )
                self.db.add(stock_log_entry)
                
                logger.info(f"✓ {stock.ticker}: {contracts_count} contracts scraped (source: {source_used})")
            
            except Exception as e:
                metrics.failed_stocks += 1
                error_msg = str(e)
                metrics.stock_errors.append({'ticker': stock.ticker, 'error': error_msg})
                failed_list.append(stock.ticker)
                
                # Log failed stock scrape
                stock_log_entry = ScraperStockLog(
                    run_id=scraper_run.id,
                    ticker=stock.ticker,
                    status=StockScrapeStatus.failed,
                    error_message=error_msg,
                    timestamp=datetime.now()
                )
                self.db.add(stock_log_entry)
                
                logger.error(f"✗ {stock.ticker}: Failed - {error_msg}", exc_info=True)
                
                # Continue with remaining stocks (don't stop entire run)
                continue
            
            finally:
                # Update progress after each stock
                update_scraper_progress(
                    completed_stocks=len(completed_list) + len(failed_list),
                    completed_stock_list=completed_list,
                    failed_stocks=failed_list
                )
                # Commit stock log entry
                if stock_log_entry:
                    self.db.commit()
        
        metrics.end_time = datetime.now()
        
        # Update scraper run record
        scraper_run.end_time = metrics.end_time
        scraper_run.status = RunStatus.completed
        scraper_run.successful_stocks = metrics.successful_stocks
        scraper_run.failed_stocks = metrics.failed_stocks
        scraper_run.total_contracts = metrics.total_contracts
        self.db.commit()
        
        # Clear progress after completion
        update_scraper_progress(
            is_running=False,
            current_stock=None,
            pending_stocks=[]
        )
        
        # Check rate limit compliance (Yahoo: 60/min, 360/hour, 8000/day)
        duration_minutes = metrics.duration_seconds() / 60 if metrics.duration_seconds() else 1
        requests_per_minute = metrics.total_api_requests / duration_minutes
        
        if requests_per_minute > 60:
            warning = f"Exceeded 60 requests/min limit: {requests_per_minute:.1f}/min"
            metrics.rate_limit_warnings.append(warning)
            logger.warning(warning)
        
        if metrics.total_api_requests > 360:
            warning = f"Scrape cycle used {metrics.total_api_requests} requests (limit: 360/hour)"
            metrics.rate_limit_warnings.append(warning)
            logger.warning(warning)
        
        logger.info(f"Scraper run {self.run_id} completed: {metrics.to_dict()}")
        
        return metrics
    
    def _get_active_watchlist(self) -> List[Stock]:
        """
        Get all active stocks from watchlist.
        
        Returns:
            List of Stock objects with status='active'
        """
        return (
            self.db.query(Stock)
            .filter(Stock.status == StockStatus.active)
            .all()
        )
    
    def _scrape_stock(self, stock: Stock) -> Tuple[int, int, str]:
        """
        Scrape options chain for a single stock.
        
        Args:
            stock: Stock object to scrape
        
        Returns:
            Tuple of (contracts_count, api_calls, source_used)
        
        Raises:
            Exception: If scraping fails
        """
        from .stock_price_service import get_stock_price_service
        from ..services.scheduler import update_scraper_progress
        
        ticker_obj = yf.Ticker(stock.ticker)
        
        # Get current stock price using multi-source service
        try:
            price_service = get_stock_price_service()
            price_result = price_service.get_price(stock.ticker)
            
            if price_result is None:
                raise ValueError("All price sources failed, trying database fallback")
            
            current_price = price_result["price"]
            source_used = price_result["source"]
            
            # Update progress with current source
            update_scraper_progress(current_source=source_used)
            logger.info(f"Using {source_used} for {stock.ticker}: ${current_price:.2f}")
            
            if not current_price or current_price <= 0:
                raise ValueError(f"Invalid price: {current_price}")
        except Exception as e:
            raise ValueError(f"Failed to fetch stock price: {e}")
        
        # Get all available expiration dates
        try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    expirations = ticker_obj.options
                    if expirations:
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for {stock.ticker} options: {e}")
                    else:
                        raise
            
            if not expirations:
                raise ValueError(f"No options available for {stock.ticker}")
        except Exception as e:
            raise ValueError(f"Failed to fetch options expirations: {e}")
        
        # Load max_expirations setting from database
        from ..models.scraper_schedule import ScraperSchedule
        config = self.db.query(ScraperSchedule).first()
        max_exp = config.max_expirations if config else 8
        
        # Limit to max expirations (nearest dates) to reduce API calls
        expirations = expirations[:max_exp]
        
        collection_timestamp = datetime.now()
        contracts_count = 0
        api_calls = 2  # 1 for price, 1 for expirations list
        
        # source_used is already set above when fetching price
        
        # Iterate through each expiration date
        for expiration_str in expirations:
            api_calls += 1  # 1 API call per option_chain() request
            try:
                # Get options chain for this expiration
                options_chain = ticker_obj.option_chain(expiration_str)
                expiration_date = datetime.strptime(expiration_str, '%Y-%m-%d').date()
                
                # Calculate days to expiry
                days_to_expiry = self.greeks_calculator.calculate_days_to_expiry(
                    expiration_date, 
                    collection_timestamp.date()
                )
                
                # Skip expired contracts
                if days_to_expiry <= 0:
                    continue
                
                # Process call options
                contracts_count += self._process_options_dataframe(
                    stock=stock,
                    options_df=options_chain.calls,
                    option_type=OptionType.call,
                    stock_price=current_price,
                    expiration_date=expiration_date,
                    days_to_expiry=days_to_expiry,
                    collection_timestamp=collection_timestamp
                )
                
                # Process put options
                contracts_count += self._process_options_dataframe(
                    stock=stock,
                    options_df=options_chain.puts,
                    option_type=OptionType.put,
                    stock_price=current_price,
                    expiration_date=expiration_date,
                    days_to_expiry=days_to_expiry,
                    collection_timestamp=collection_timestamp
                )
            
            except Exception as e:
                logger.warning(f"Failed to process expiration {expiration_str} for {stock.ticker}: {e}")
                # Continue with next expiration
                continue
        
        # Commit all contracts for this stock
        self.db.commit()
        
        logger.info(f"Scraped {contracts_count} contracts for {stock.ticker} ({api_calls} API calls)")
        return contracts_count, api_calls, source_used
    
    def _process_options_dataframe(
        self,
        stock: Stock,
        options_df,
        option_type: OptionType,
        stock_price: float,
        expiration_date: date,
        days_to_expiry: int,
        collection_timestamp: datetime
    ) -> int:
        """
        Process options DataFrame and create HistoricalPremiumRecord entries.
        
        Args:
            stock: Stock object
            options_df: Pandas DataFrame with options data from yfinance
            option_type: OptionType (call or put)
            stock_price: Current stock price
            expiration_date: Option expiration date
            days_to_expiry: Days until expiration
            collection_timestamp: Time of data collection
        
        Returns:
            Number of contracts processed
        """
        contracts_count = 0
        
        for _, row in options_df.iterrows():
            try:
                strike_price = float(row['strike'])
                
                # Get premium (prefer lastPrice, fallback to bid/ask midpoint)
                premium = row.get('lastPrice')
                if premium is None or premium == 0:
                    bid = row.get('bid', 0)
                    ask = row.get('ask', 0)
                    if bid > 0 and ask > 0:
                        premium = (bid + ask) / 2
                    else:
                        premium = bid or ask
                
                # Skip if no valid premium
                if premium is None or premium <= 0:
                    continue
                
                # Get implied volatility
                implied_volatility = row.get('impliedVolatility')
                if implied_volatility is None or implied_volatility <= 0:
                    # Cannot calculate Greeks without IV
                    greeks = {
                        'delta': None,
                        'gamma': None,
                        'theta': None,
                        'vega': None,
                        'rho': None
                    }
                else:
                    # Calculate Greeks
                    greeks = self.greeks_calculator.calculate_greeks(
                        stock_price=stock_price,
                        strike_price=strike_price,
                        time_to_expiry_days=days_to_expiry,
                        implied_volatility=implied_volatility,
                        option_type=option_type.value
                    )
                
                # Determine contract status
                contract_status = ContractStatus.active if days_to_expiry > 0 else ContractStatus.expired
                
                # Create record
                record = HistoricalPremiumRecord(
                    stock_id=stock.stock_id,
                    collection_timestamp=collection_timestamp,
                    option_type=option_type,
                    strike_price=strike_price,
                    expiration_date=expiration_date,
                    days_to_expiry=days_to_expiry,
                    contract_status=contract_status,
                    premium=premium,
                    stock_price_at_collection=stock_price,
                    implied_volatility=implied_volatility,
                    delta=greeks['delta'],
                    gamma=greeks['gamma'],
                    theta=greeks['theta'],
                    vega=greeks['vega'],
                    rho=greeks['rho'],
                    volume=int(row.get('volume')) if row.get('volume') and not pd.isna(row.get('volume')) else None,
                    open_interest=int(row.get('openInterest')) if row.get('openInterest') and not pd.isna(row.get('openInterest')) else None,
                    data_source='yahoo_finance',
                    scraper_run_id=self.run_id
                )
                
                self.db.add(record)
                contracts_count += 1
            
            except Exception as e:
                logger.warning(f"Failed to process contract for {stock.ticker} strike {row.get('strike')}: {e}")
                # Continue with next contract
                continue
        
        return contracts_count
    
    def mark_expired_contracts(self) -> int:
        """
        Mark contracts as expired if past expiration_date.
        
        Returns:
            Number of contracts marked as expired
        """
        today = datetime.now().date()
        
        result = (
            self.db.query(HistoricalPremiumRecord)
            .filter(
                and_(
                    HistoricalPremiumRecord.expiration_date < today,
                    HistoricalPremiumRecord.contract_status == ContractStatus.active
                )
            )
            .update({HistoricalPremiumRecord.contract_status: ContractStatus.expired})
        )
        
        self.db.commit()
        
        logger.info(f"Marked {result} contracts as expired")
        
        return result


def create_scraper(db: Session) -> YahooFinanceScraper:
    """
    Factory function to create a scraper instance.
    
    Args:
        db: SQLAlchemy database session
    
    Returns:
        YahooFinanceScraper instance
    """
    return YahooFinanceScraper(db)
