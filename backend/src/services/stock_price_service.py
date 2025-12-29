"""
Multi-Source Stock Price Service

Rotates between multiple data sources to avoid rate limiting:
1. Yahoo Finance (yfinance)
2. Alpha Vantage API
3. Finnhub API
4. Fallback to database

Tracks source health and intelligently routes requests.
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from enum import Enum
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
import finnhub
import os

logger = logging.getLogger(__name__)


class PriceSource(Enum):
    """Available price data sources"""
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    DATABASE = "database"


class SourceHealth:
    """Track health status of each data source"""
    
    def __init__(self):
        self.last_success: Dict[PriceSource, datetime] = {}
        self.last_failure: Dict[PriceSource, datetime] = {}
        self.failure_count: Dict[PriceSource, int] = {source: 0 for source in PriceSource}
        self.cooldown_until: Dict[PriceSource, datetime] = {}
    
    def record_success(self, source: PriceSource):
        """Record successful fetch from source"""
        self.last_success[source] = datetime.now()
        self.failure_count[source] = 0
        if source in self.cooldown_until:
            del self.cooldown_until[source]
        logger.debug(f"{source.value} - Success recorded")
    
    def record_failure(self, source: PriceSource, cooldown_minutes: int = 30):
        """Record failed fetch from source and set cooldown"""
        self.last_failure[source] = datetime.now()
        self.failure_count[source] += 1
        
        # Exponential backoff: 30min, 1hr, 2hr, 4hr
        cooldown_multiplier = min(2 ** (self.failure_count[source] - 1), 8)
        cooldown = timedelta(minutes=cooldown_minutes * cooldown_multiplier)
        self.cooldown_until[source] = datetime.now() + cooldown
        
        logger.warning(
            f"{source.value} - Failure #{self.failure_count[source]}, "
            f"cooldown until {self.cooldown_until[source].strftime('%H:%M:%S')}"
        )
    
    def is_available(self, source: PriceSource) -> bool:
        """Check if source is available (not in cooldown)"""
        if source not in self.cooldown_until:
            return True
        
        if datetime.now() >= self.cooldown_until[source]:
            del self.cooldown_until[source]
            return True
        
        return False
    
    def get_next_available_sources(self) -> List[PriceSource]:
        """Get list of sources sorted by priority and availability"""
        sources = [
            PriceSource.YAHOO_FINANCE,
            PriceSource.ALPHA_VANTAGE,
            PriceSource.FINNHUB
        ]
        
        # Filter out sources in cooldown
        available = [s for s in sources if self.is_available(s)]
        
        # Sort by failure count (least failures first)
        available.sort(key=lambda s: self.failure_count[s])
        
        return available


class StockPriceService:
    """Service to fetch stock prices from multiple sources with rotation"""
    
    def __init__(self):
        self.health = SourceHealth()
        
        # API keys from environment (optional)
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
        
        # Initialize API clients
        if self.alpha_vantage_key:
            self.alpha_vantage = TimeSeries(key=self.alpha_vantage_key, output_format='json')
            logger.info("Alpha Vantage client initialized")
        else:
            self.alpha_vantage = None
            logger.warning("Alpha Vantage API key not found - this source will be skipped")
        
        if self.finnhub_key:
            self.finnhub_client = finnhub.Client(api_key=self.finnhub_key)
            logger.info("Finnhub client initialized")
        else:
            self.finnhub_client = None
            logger.warning("Finnhub API key not found - this source will be skipped")
    
    def fetch_from_yahoo(self, ticker: str) -> Optional[float]:
        """Fetch price from Yahoo Finance"""
        try:
            yf_ticker = yf.Ticker(ticker.upper())
            
            # Try info first
            info = yf_ticker.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            if price:
                return float(price)
            
            # Try history as fallback
            hist = yf_ticker.history(period='1d')
            if not hist.empty and 'Close' in hist.columns:
                return float(hist['Close'].iloc[-1])
            
            return None
            
        except Exception as e:
            logger.error(f"Yahoo Finance error for {ticker}: {e}")
            return None
    
    def fetch_from_alpha_vantage(self, ticker: str) -> Optional[float]:
        """Fetch price from Alpha Vantage"""
        if not self.alpha_vantage:
            return None
        
        try:
            data, _ = self.alpha_vantage.get_quote_endpoint(symbol=ticker.upper())
            
            if '05. price' in data:
                return float(data['05. price'])
            
            return None
            
        except Exception as e:
            logger.error(f"Alpha Vantage error for {ticker}: {e}")
            return None
    
    def fetch_from_finnhub(self, ticker: str) -> Optional[float]:
        """Fetch price from Finnhub"""
        if not self.finnhub_client:
            return None
        
        try:
            quote = self.finnhub_client.quote(ticker.upper())
            
            if quote and 'c' in quote and quote['c'] > 0:
                return float(quote['c'])  # 'c' is current price
            
            return None
            
        except Exception as e:
            logger.error(f"Finnhub error for {ticker}: {e}")
            return None
    
    def get_live_price(self, ticker: str) -> Optional[Dict]:
        """
        Get live stock price using source rotation.
        
        Returns dict with:
        - price: float
        - source: str (name of source used)
        - timestamp: datetime
        """
        available_sources = self.health.get_next_available_sources()
        
        if not available_sources:
            logger.warning("All sources are in cooldown, will try all anyway")
            available_sources = [
                PriceSource.YAHOO_FINANCE,
                PriceSource.ALPHA_VANTAGE,
                PriceSource.FINNHUB
            ]
        
        logger.info(f"Fetching price for {ticker}, trying sources: {[s.value for s in available_sources]}")
        
        for source in available_sources:
            try:
                price = None
                
                if source == PriceSource.YAHOO_FINANCE:
                    price = self.fetch_from_yahoo(ticker)
                elif source == PriceSource.ALPHA_VANTAGE:
                    price = self.fetch_from_alpha_vantage(ticker)
                elif source == PriceSource.FINNHUB:
                    price = self.fetch_from_finnhub(ticker)
                
                if price is not None:
                    self.health.record_success(source)
                    logger.info(f"Successfully fetched {ticker} price ${price:.2f} from {source.value}")
                    return {
                        "price": price,
                        "source": source.value,
                        "timestamp": datetime.now()
                    }
                else:
                    # Source returned None but didn't raise exception
                    logger.warning(f"{source.value} returned None for {ticker}")
                    
            except Exception as e:
                logger.error(f"Error fetching from {source.value} for {ticker}: {e}")
                self.health.record_failure(source)
        
        logger.error(f"All sources failed for {ticker}")
        return None


# Global service instance
_stock_price_service: Optional[StockPriceService] = None


def get_stock_price_service() -> StockPriceService:
    """Get or create the global stock price service instance"""
    global _stock_price_service
    
    if _stock_price_service is None:
        _stock_price_service = StockPriceService()
    
    return _stock_price_service
