"""
Premium Query Service

Implements business logic for querying historical premium data with:
- Three strike matching modes (exact, percentage_range, nearest)
- Duration matching with tolerance
- Statistical aggregations (min/max/avg, Greeks)
- Lookback time windows

References:
- data-model.md: Query patterns and indexes
- spec.md: User Story 1 requirements
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from ..models.historical_premium_record import HistoricalPremiumRecord, OptionType
from ..models.stock import Stock
from ..models.schemas import (
    PremiumQueryRequest,
    PremiumQueryResponse,
    PremiumStatistics,
    StrikeModeType
)

logger = logging.getLogger(__name__)


class QueryService:
    """Service for querying and aggregating historical premium data"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def query_premium_statistics(self, request: PremiumQueryRequest) -> PremiumQueryResponse:
        """
        Query historical premium statistics based on request parameters.
        
        Args:
            request: Query parameters (ticker, option_type, strike matching, duration, lookback)
        
        Returns:
            PremiumQueryResponse with aggregated statistics per strike
        
        Raises:
            ValueError: If ticker not found or invalid parameters
        """
        # Validate ticker exists
        stock = self.db.query(Stock).filter(Stock.ticker == request.ticker.upper()).first()
        if not stock:
            raise ValueError(f"Stock ticker '{request.ticker}' not found in database")
        
        # Calculate time window
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=request.lookback_days)
        
        # Build base query
        base_query = self.db.query(HistoricalPremiumRecord).filter(
            and_(
                HistoricalPremiumRecord.stock_id == stock.stock_id,
                HistoricalPremiumRecord.option_type == request.option_type,
                HistoricalPremiumRecord.collection_timestamp >= start_time,
                HistoricalPremiumRecord.collection_timestamp <= end_time
            )
        )
        
        # Apply duration filter if specified
        if request.duration_days is not None:
            tolerance = request.duration_tolerance_days
            min_dte = request.duration_days - tolerance
            max_dte = request.duration_days + tolerance
            base_query = base_query.filter(
                and_(
                    HistoricalPremiumRecord.days_to_expiry >= min_dte,
                    HistoricalPremiumRecord.days_to_expiry <= max_dte
                )
            )
        
        # Apply strike filter based on mode
        if request.strike_mode == StrikeModeType.exact:
            strike_prices = self._get_exact_strikes(base_query, request.strike_price)
        elif request.strike_mode == StrikeModeType.percentage_range:
            strike_prices = self._get_range_strikes(base_query, request.strike_price, request.strike_range_percent)
        elif request.strike_mode == StrikeModeType.nearest:
            strike_prices = self._get_nearest_strikes(
                base_query,
                stock.stock_id,
                request.option_type,
                request.nearest_count_above,
                request.nearest_count_below
            )
        else:
            raise ValueError(f"Invalid strike_mode: {request.strike_mode}")
        
        # Get aggregated statistics for each strike
        statistics = self._aggregate_statistics(base_query, strike_prices)
        
        # Build response
        return PremiumQueryResponse(
            ticker=request.ticker.upper(),
            option_type=request.option_type.value,
            strike_mode=request.strike_mode.value,
            duration_days=request.duration_days,
            lookback_days=request.lookback_days,
            results=statistics,
            total_strikes=len(statistics),
            total_data_points=sum(s.data_points for s in statistics)
        )
    
    def _get_exact_strikes(self, base_query, strike_price: Decimal) -> List[Decimal]:
        """Get exact strike price match"""
        return [strike_price]
    
    def _get_range_strikes(
        self,
        base_query,
        target_strike: Decimal,
        range_percent: float
    ) -> List[Decimal]:
        """
        Get all strikes within percentage range of target.
        
        Example: target=$100, range=10% => strikes between $90-$110
        """
        range_multiplier = Decimal(range_percent) / Decimal(100)
        min_strike = target_strike * (Decimal(1) - range_multiplier)
        max_strike = target_strike * (Decimal(1) + range_multiplier)
        
        # Get distinct strikes in range from actual data
        strikes = self.db.query(HistoricalPremiumRecord.strike_price).filter(
            and_(
                HistoricalPremiumRecord.strike_price >= min_strike,
                HistoricalPremiumRecord.strike_price <= max_strike
            )
        ).distinct().all()
        
        return [s[0] for s in strikes] if strikes else []
    
    def _get_nearest_strikes(
        self,
        base_query,
        stock_id: int,
        option_type: OptionType,
        count_above: Optional[int],
        count_below: Optional[int]
    ) -> List[Decimal]:
        """
        Get N nearest strikes above and/or below current stock price.
        
        Uses most recent stock_price_at_collection from data.
        """
        # Get current price from most recent data point
        recent_record = base_query.order_by(HistoricalPremiumRecord.collection_timestamp.desc()).first()
        if not recent_record:
            logger.warning(f"No data found for stock {stock_id} to determine current price")
            return []
        
        current_price = recent_record.stock_price_at_collection
        logger.info(f"Using current price ${current_price} for nearest strikes matching")
        
        # Get all distinct strikes from the filtered data (use subquery)
        all_strikes_in_query = base_query.with_entities(
            HistoricalPremiumRecord.strike_price
        ).distinct().all()
        
        all_strikes = sorted([s[0] for s in all_strikes_in_query])
        
        if not all_strikes:
            return []
        
        strikes = []
        
        # Get strikes above current price
        if count_above and count_above > 0:
            strikes_above = [s for s in all_strikes if s > current_price][:count_above]
            strikes.extend(strikes_above)
        
        # Get strikes below current price
        if count_below and count_below > 0:
            strikes_below = [s for s in reversed(all_strikes) if s < current_price][:count_below]
            strikes.extend(strikes_below)
        
        return sorted(set(strikes))
    
    def _aggregate_statistics(
        self,
        base_query,
        strike_prices: List[Decimal]
    ) -> List[PremiumStatistics]:
        """
        Aggregate premium statistics for each strike price.
        
        Calculates: MIN/MAX/AVG premium, AVG Greeks, data point count, time range
        """
        if not strike_prices:
            return []
        
        statistics = []
        
        for strike_price in strike_prices:
            # Query all records for this strike
            records = base_query.filter(
                HistoricalPremiumRecord.strike_price == strike_price
            ).all()
            
            if not records:
                continue
            
            # Calculate aggregations
            premiums = [r.premium for r in records]
            
            # Premium statistics
            min_premium = min(premiums)
            max_premium = max(premiums)
            avg_premium = sum(premiums) / len(premiums)
            
            # Median (sort and take middle value)
            sorted_premiums = sorted(premiums)
            n = len(sorted_premiums)
            if n % 2 == 0:
                median_premium = (sorted_premiums[n//2 - 1] + sorted_premiums[n//2]) / 2
            else:
                median_premium = sorted_premiums[n//2]
            
            # Standard deviation
            mean = avg_premium
            variance = sum((p - mean) ** 2 for p in premiums) / len(premiums)
            std_premium = Decimal(float(variance) ** 0.5)
            
            # Greeks averages (filter out None values)
            deltas = [r.delta for r in records if r.delta is not None]
            gammas = [r.gamma for r in records if r.gamma is not None]
            thetas = [r.theta for r in records if r.theta is not None]
            vegas = [r.vega for r in records if r.vega is not None]
            
            avg_delta = sum(deltas) / len(deltas) if deltas else None
            avg_gamma = sum(gammas) / len(gammas) if gammas else None
            avg_theta = sum(thetas) / len(thetas) if thetas else None
            avg_vega = sum(vegas) / len(vegas) if vegas else None
            
            # Time range
            timestamps = [r.collection_timestamp for r in records]
            first_seen = min(timestamps)
            last_seen = max(timestamps)
            
            statistics.append(PremiumStatistics(
                strike_price=strike_price,
                min_premium=min_premium,
                max_premium=max_premium,
                avg_premium=avg_premium,
                median_premium=median_premium,
                std_premium=std_premium,
                avg_delta=avg_delta,
                avg_gamma=avg_gamma,
                avg_theta=avg_theta,
                avg_vega=avg_vega,
                data_points=len(records),
                first_seen=first_seen,
                last_seen=last_seen
            ))
        
        # Sort by strike price
        statistics.sort(key=lambda s: s.strike_price)
        
        return statistics


def get_query_service(db: Session) -> QueryService:
    """Dependency injection helper"""
    return QueryService(db)
