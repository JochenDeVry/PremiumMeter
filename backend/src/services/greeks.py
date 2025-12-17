"""
Black-Scholes Greeks Calculator

Calculates option Greeks (delta, gamma, theta, vega, rho) using the Black-Scholes model.
Uses scipy.stats for cumulative normal distribution calculations.

References:
- research.md: Black-Scholes implementation strategy
- data-model.md: Greeks storage in HistoricalPremiumRecord
"""

import numpy as np
from scipy.stats import norm
from datetime import datetime, date
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class GreeksCalculator:
    """
    Black-Scholes Greeks calculator for options pricing.
    
    All Greeks are calculated using the standard Black-Scholes formula with:
    - Stock price (S): Current underlying price
    - Strike price (K): Contract strike
    - Time to expiry (T): Years until expiration
    - Risk-free rate (r): Annualized risk-free rate
    - Implied volatility (sigma): Annualized volatility
    """
    
    def __init__(self, risk_free_rate: float = 0.045):
        """
        Initialize Greeks calculator.
        
        Args:
            risk_free_rate: Annualized risk-free rate (default: 4.5%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_greeks(
        self,
        stock_price: float,
        strike_price: float,
        time_to_expiry_days: int,
        implied_volatility: float,
        option_type: str = 'call'
    ) -> Dict[str, Optional[float]]:
        """
        Calculate all Greeks for an option contract.
        
        Args:
            stock_price: Current stock price
            strike_price: Option strike price
            time_to_expiry_days: Days until expiration
            implied_volatility: Implied volatility (annualized, e.g., 0.25 for 25%)
            option_type: 'call' or 'put'
        
        Returns:
            Dictionary with delta, gamma, theta, vega, rho (None if calculation fails)
        """
        try:
            # Validate inputs
            if stock_price <= 0 or strike_price <= 0:
                logger.warning(f"Invalid price inputs: S={stock_price}, K={strike_price}")
                return self._null_greeks()
            
            if time_to_expiry_days <= 0:
                logger.warning(f"Invalid time to expiry: {time_to_expiry_days} days")
                return self._null_greeks()
            
            if implied_volatility <= 0:
                logger.warning(f"Invalid implied volatility: {implied_volatility}")
                return self._null_greeks()
            
            # Convert days to years
            T = time_to_expiry_days / 365.0
            S = stock_price
            K = strike_price
            r = self.risk_free_rate
            sigma = implied_volatility
            
            # Calculate d1 and d2
            d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            
            # Calculate Greeks based on option type
            if option_type.lower() == 'call':
                delta = norm.cdf(d1)
                theta = (
                    -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                    - r * K * np.exp(-r * T) * norm.cdf(d2)
                )
                rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100  # Per 1% rate change
            else:  # put
                delta = -norm.cdf(-d1)
                theta = (
                    -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                    + r * K * np.exp(-r * T) * norm.cdf(-d2)
                )
                rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100  # Per 1% rate change
            
            # Gamma and Vega are same for calls and puts
            gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
            vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% volatility change
            
            # Convert theta to daily (from annualized)
            theta_daily = theta / 365
            
            return {
                'delta': round(delta, 6),
                'gamma': round(gamma, 6),
                'theta': round(theta_daily, 6),
                'vega': round(vega, 6),
                'rho': round(rho, 6)
            }
        
        except Exception as e:
            logger.error(f"Greeks calculation failed: {e}", exc_info=True)
            return self._null_greeks()
    
    def _null_greeks(self) -> Dict[str, None]:
        """Return dictionary with null Greeks when calculation fails."""
        return {
            'delta': None,
            'gamma': None,
            'theta': None,
            'vega': None,
            'rho': None
        }
    
    def calculate_days_to_expiry(
        self,
        expiration_date: date,
        collection_date: Optional[date] = None
    ) -> int:
        """
        Calculate days to expiration from collection date.
        
        Args:
            expiration_date: Option expiration date
            collection_date: Data collection date (default: today)
        
        Returns:
            Number of days until expiration (0 if already expired)
        """
        if collection_date is None:
            collection_date = datetime.now().date()
        
        days = (expiration_date - collection_date).days
        return max(0, days)  # Cannot be negative


# Singleton instance
_calculator = None


def get_greeks_calculator(risk_free_rate: float = 0.045) -> GreeksCalculator:
    """
    Get or create the singleton GreeksCalculator instance.
    
    Args:
        risk_free_rate: Annualized risk-free rate (default: 4.5%)
    
    Returns:
        GreeksCalculator instance
    """
    global _calculator
    if _calculator is None:
        _calculator = GreeksCalculator(risk_free_rate)
    return _calculator
