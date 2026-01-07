# Real-Time Trading Hours Integration

## Current Implementation
Market hours are currently **static** and configured in the database:
- **Default**: 09:30:00 - 16:00:00 (America/New_York)
- **Timezone**: Stored as IANA timezone string
- **Location**: `scraper_schedule` table

## Proposed: Dynamic Trading Hours

### Why Dynamic Hours?
- **Early closures**: US markets close early on certain days (e.g., day before Thanksgiving at 1:00 PM)
- **Holidays**: Markets closed on federal holidays
- **Special events**: Occasional closures for emergencies or special circumstances

### Available APIs

#### 1. **Polygon.io** (Recommended)
- **Endpoint**: `/v1/marketstatus/now`
- **Features**:
  - Real-time market status (open/closed)
  - Extended hours information
  - Multiple exchanges (NYSE, NASDAQ, etc.)
- **Cost**: Free tier available (5 API calls/minute)
- **Documentation**: https://polygon.io/docs/stocks/get_v1_marketstatus_now

```python
# Example response
{
  "market": "open",
  "serverTime": "2024-01-15T14:30:00.000Z",
  "exchanges": {
    "nasdaq": "open",
    "nyse": "open"
  },
  "currencies": {
    "fx": "open",
    "crypto": "open"
  }
}
```

#### 2. **Tradier**
- **Endpoint**: `/v1/markets/clock`
- **Features**:
  - Current market status
  - Next open/close times
  - Description of market state
- **Cost**: Free tier available
- **Documentation**: https://documentation.tradier.com/brokerage-api/markets/get-clock

```python
# Example response
{
  "clock": {
    "date": "2024-01-15",
    "description": "Market is open",
    "state": "open",
    "timestamp": 1705334400,
    "next_change": "16:00",
    "next_state": "closed"
  }
}
```

#### 3. **Alpha Vantage**
- **Endpoint**: Market status not directly available, but can use `/query?function=TIME_SERIES_INTRADAY`
- **Limitation**: No direct market hours API
- **Not recommended** for this use case

#### 4. **Yahoo Finance** (Unofficial)
- **Endpoint**: Scrape from market summary pages
- **Risk**: Unofficial API, may break without notice
- **Not recommended** for production

### Implementation Plan

#### Backend Changes

**1. Create new service: `backend/src/services/market_hours_service.py`**
```python
import requests
from datetime import datetime, time
import pytz
from typing import Tuple, Optional

class MarketHoursService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
    
    async def get_current_market_status(self) -> dict:
        """Get current market status from Polygon.io"""
        url = f"{self.base_url}/v1/marketstatus/now"
        params = {"apiKey": self.api_key}
        response = requests.get(url, params=params)
        return response.json()
    
    async def get_market_hours(self, date: datetime) -> Tuple[time, time]:
        """
        Get market hours for a specific date.
        Returns (open_time, close_time) in America/New_York timezone.
        """
        # Check if holiday or early closure
        status = await self.get_current_market_status()
        
        # Default hours
        open_time = time(9, 30, 0)
        close_time = time(16, 0, 0)
        
        # Adjust for early closure days
        if self._is_early_close_day(date):
            close_time = time(13, 0, 0)  # 1:00 PM close
        
        return open_time, close_time
    
    def _is_early_close_day(self, date: datetime) -> bool:
        """Check if date is an early closure day"""
        # Day before Thanksgiving
        # July 3rd if July 4th is on weekday
        # Christmas Eve if on weekday
        # etc.
        pass
```

**2. Add new API endpoint: `backend/src/api/endpoints/market_hours.py`**
```python
@router.get("/api/market-hours/current")
async def get_current_market_hours():
    """Get current market hours considering holidays and special closures"""
    service = get_market_hours_service()
    status = await service.get_current_market_status()
    
    return {
        "market_open": status.get("market") == "open",
        "hours_start": "09:30:00",
        "hours_end": "16:00:00",
        "is_early_close": False,
        "next_open": None,
        "description": "Regular trading hours"
    }
```

**3. Update scheduler to check market hours on each run**
```python
# In scheduler.py
async def _scraper_job_wrapper(self):
    # Before starting scrape, check if market is actually open
    market_hours_service = get_market_hours_service()
    is_open = await market_hours_service.is_market_open()
    
    if not is_open:
        logger.info("Market is closed, skipping scrape")
        return
    
    # Continue with scrape...
```

#### Frontend Changes

**1. Add API call in SchedulerConfigPanel.tsx**
```typescript
const [actualMarketHours, setActualMarketHours] = useState<any>(null);

useEffect(() => {
  const loadActualMarketHours = async () => {
    try {
      const hours = await apiClient.getCurrentMarketHours();
      setActualMarketHours(hours);
    } catch (err) {
      console.error('Failed to load actual market hours:', err);
    }
  };
  
  loadActualMarketHours();
  // Refresh every 5 minutes
  const interval = setInterval(loadActualMarketHours, 5 * 60 * 1000);
  return () => clearInterval(interval);
}, []);
```

**2. Display actual vs configured hours**
```tsx
<div className="config-section">
  <h3>Market Hours</h3>
  
  {actualMarketHours && (
    <div className="market-status-alert">
      <span className={actualMarketHours.market_open ? 'status-open' : 'status-closed'}>
        Market is currently {actualMarketHours.market_open ? 'OPEN' : 'CLOSED'}
      </span>
      {actualMarketHours.is_early_close && (
        <span className="early-close-warning">⚠ Early closure today at {actualMarketHours.hours_end}</span>
      )}
    </div>
  )}
  
  {/* Rest of market hours display */}
</div>
```

### Environment Variables

Add to `.env`:
```bash
# Market Hours API
POLYGON_API_KEY=your_polygon_api_key_here
MARKET_HOURS_CHECK_ENABLED=true
```

### Configuration Steps

1. **Sign up for Polygon.io**
   - Go to https://polygon.io
   - Create free account (5 calls/min)
   - Get API key

2. **Add to backend requirements**
   ```bash
   pip install polygon-api-client
   ```

3. **Update docker-compose environment**
   ```yaml
   backend:
     environment:
       POLYGON_API_KEY: ${POLYGON_API_KEY}
       MARKET_HOURS_CHECK_ENABLED: ${MARKET_HOURS_CHECK_ENABLED:-false}
   ```

4. **Deploy changes**

### Fallback Strategy

If API is unavailable or rate limit exceeded:
1. Use configured static hours as fallback
2. Log warning
3. Display message to user that dynamic hours are unavailable
4. Continue with static schedule

### Costs & Limitations

**Polygon.io Free Tier:**
- 5 API calls per minute
- Unlimited markets
- Delayed data (15 minutes)
- **Sufficient for our use case** (we only need to check once per scraper run)

**Recommended**:
- Cache market hours for the day (refresh once at midnight)
- Only make API call when scheduler starts or at day boundary
- Reduces API calls to ~1-2 per day

### Testing

1. **Test early closure**: Mock date to day before Thanksgiving
2. **Test holiday**: Mock date to Christmas Day
3. **Test API failure**: Verify fallback to static hours
4. **Test rate limiting**: Ensure graceful degradation

### Alternative: Static Calendar

If you prefer not to use external APIs, create a static JSON calendar:

```json
{
  "2024": {
    "early_closures": [
      "2024-07-03",
      "2024-11-29",
      "2024-12-24"
    ],
    "closures": [
      "2024-01-01",
      "2024-01-15",
      "2024-02-19",
      "2024-03-29",
      "2024-05-27",
      "2024-06-19",
      "2024-07-04",
      "2024-09-02",
      "2024-11-28",
      "2024-12-25"
    ]
  }
}
```

This requires annual updates but has no API dependencies.

## Recommendation

**For MVP/Current State:**
- Keep static hours (current implementation)
- Add note in UI about potential variations
- ✅ **Already implemented**: Timezone switcher to view hours in Brussels time

**For Future Enhancement:**
- Integrate Polygon.io API with free tier
- Implement caching to minimize API calls
- Add visual indicator when market is closed or early closure
- Show countdown to next market open

The timezone switcher addresses your immediate need to view hours in Brussels time. The dynamic hours fetching would be a nice enhancement but requires external API integration and ongoing maintenance.
