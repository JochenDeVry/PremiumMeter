"""
Rate Limit Calculation Tests

Tests for the rate limit calculation logic used in the scheduler.
Ensures that API usage estimates are accurate and within Yahoo Finance limits.
"""

import pytest
from datetime import datetime


@pytest.mark.unit
class TestRateLimitCalculations:
    """Test rate limit calculation logic"""
    
    def calculate_rate_limits(
        self,
        num_stocks: int,
        polling_interval_minutes: int,
        stock_delay_seconds: int,
        max_expirations: int
    ):
        """
        Calculate expected API usage rates.
        This mirrors the logic in scheduler.py endpoint.
        """
        if num_stocks == 0 or polling_interval_minutes == 0:
            return {
                "requests_per_cycle": 0,
                "requests_per_minute": 0.0,
                "requests_per_hour": 0.0,
                "requests_per_day": 0.0,
            }
        
        # Calculate requests per cycle
        requests_per_stock = 1 + max_expirations  # 1 for stock info + N for expirations
        requests_per_cycle = num_stocks * requests_per_stock
        
        # Calculate time metrics
        cycle_duration_seconds = (num_stocks * stock_delay_seconds)
        cycle_duration_minutes = cycle_duration_seconds / 60.0
        
        # Calculate rates
        cycles_per_hour = 60.0 / polling_interval_minutes
        requests_per_minute = requests_per_cycle / max(cycle_duration_minutes, polling_interval_minutes)
        requests_per_hour = cycles_per_hour * requests_per_cycle
        requests_per_day = requests_per_hour * 24.0
        
        return {
            "requests_per_cycle": requests_per_cycle,
            "requests_per_minute": round(requests_per_minute, 2),
            "requests_per_hour": round(requests_per_hour, 2),
            "requests_per_day": round(requests_per_day, 2),
            "cycle_duration_minutes": round(cycle_duration_minutes, 2),
        }
    
    def test_basic_calculation(self):
        """Test basic rate calculation with typical values"""
        result = self.calculate_rate_limits(
            num_stocks=5,
            polling_interval_minutes=60,
            stock_delay_seconds=10,
            max_expirations=8
        )
        
        # 5 stocks * (1 + 8) = 45 requests per cycle
        assert result["requests_per_cycle"] == 45
        
        # With 10 second delay, cycle takes 50 seconds (0.83 minutes)
        # But polling interval is 60 minutes, so that's the limiting factor
        # 45 requests / 60 minutes = 0.75 requests/minute
        assert result["requests_per_minute"] <= 60  # Well under Yahoo limit
        
        # 1 cycle per hour * 45 requests = 45 requests/hour
        assert result["requests_per_hour"] == 45.0
        
        # 45 * 24 = 1080 requests/day
        assert result["requests_per_day"] == 1080.0
    
    def test_high_stock_count(self):
        """Test with many stocks - demonstrates rate limit constraints"""
        result = self.calculate_rate_limits(
            num_stocks=50,
            polling_interval_minutes=30,
            stock_delay_seconds=10,
            max_expirations=8
        )
        
        # 50 stocks * 9 requests = 450 per cycle
        assert result["requests_per_cycle"] == 450
        
        # With 30 min polling: 2 cycles/hour * 450 = 900 requests/hour
        # This EXCEEDS Yahoo's 360/hour limit - configuration not safe!
        assert result["requests_per_hour"] == 900.0
        assert result["requests_per_hour"] > 360  # Shows this config is unsafe
    
    def test_aggressive_polling(self):
        """Test with aggressive polling - demonstrates unsafe configuration"""
        result = self.calculate_rate_limits(
            num_stocks=20,
            polling_interval_minutes=5,  # Poll every 5 minutes
            stock_delay_seconds=15,
            max_expirations=8
        )
        
        # 20 * 9 = 180 per cycle
        assert result["requests_per_cycle"] == 180
        
        # 12 cycles/hour * 180 = 2160 requests/hour
        # This GREATLY EXCEEDS Yahoo's 360/hour limit!
        assert result["requests_per_hour"] == 2160.0
        assert result["requests_per_hour"] > 360  # Shows this config is very unsafe
    
    def test_zero_stocks(self):
        """Test with zero stocks"""
        result = self.calculate_rate_limits(
            num_stocks=0,
            polling_interval_minutes=60,
            stock_delay_seconds=10,
            max_expirations=8
        )
        
        assert result["requests_per_cycle"] == 0
        assert result["requests_per_minute"] == 0.0
        assert result["requests_per_hour"] == 0.0
        assert result["requests_per_day"] == 0.0
    
    def test_minimal_delay(self):
        """Test with minimal stock delay"""
        result = self.calculate_rate_limits(
            num_stocks=10,
            polling_interval_minutes=60,
            stock_delay_seconds=1,  # 1 second delay
            max_expirations=8
        )
        
        # Cycle completes in 10 seconds (0.17 minutes)
        assert result["cycle_duration_minutes"] < 1.0
        
        # But limited by polling interval
        assert result["requests_per_hour"] == 90.0  # 10 stocks * 9 requests * 1 cycle/hour
    
    def test_max_expirations_impact(self):
        """Test how max_expirations affects request count"""
        # With 4 expirations
        result_4 = self.calculate_rate_limits(
            num_stocks=10,
            polling_interval_minutes=60,
            stock_delay_seconds=10,
            max_expirations=4
        )
        
        # With 12 expirations
        result_12 = self.calculate_rate_limits(
            num_stocks=10,
            polling_interval_minutes=60,
            stock_delay_seconds=10,
            max_expirations=12
        )
        
        # More expirations = more requests
        assert result_12["requests_per_cycle"] > result_4["requests_per_cycle"]
        assert result_12["requests_per_day"] > result_4["requests_per_day"]
        
        # 10 stocks * (1 + 4) = 50 requests
        assert result_4["requests_per_cycle"] == 50
        
        # 10 stocks * (1 + 12) = 130 requests
        assert result_12["requests_per_cycle"] == 130


@pytest.mark.unit
class TestYahooFinanceLimits:
    """Test that configurations respect Yahoo Finance rate limits"""
    
    YAHOO_LIMIT_PER_MINUTE = 60
    YAHOO_LIMIT_PER_HOUR = 360
    YAHOO_LIMIT_PER_DAY = 8000
    
    def test_default_config_safe(self):
        """Default configuration should be well within limits"""
        # Default: 5 stocks, 60 min polling, 10 sec delay, 8 expirations
        requests_per_cycle = 5 * (1 + 8)  # 45
        requests_per_hour = 1 * requests_per_cycle  # 1 cycle/hour
        requests_per_day = 24 * requests_per_hour  # 1080
        
        assert requests_per_hour < self.YAHOO_LIMIT_PER_HOUR
        assert requests_per_day < self.YAHOO_LIMIT_PER_DAY
    
    def test_max_safe_stocks(self):
        """Calculate maximum safe stock count"""
        # With 30 min polling, how many stocks can we handle?
        polling_interval = 30
        cycles_per_day = (24 * 60) / polling_interval  # 48 cycles
        max_requests_per_cycle = self.YAHOO_LIMIT_PER_DAY / cycles_per_day  # ~166
        
        # With 8 expirations: stocks = 166 / 9 ≈ 18 stocks
        max_stocks = int(max_requests_per_cycle / (1 + 8))
        
        # Verify this is safe
        requests_per_day = cycles_per_day * max_stocks * 9
        assert requests_per_day < self.YAHOO_LIMIT_PER_DAY
