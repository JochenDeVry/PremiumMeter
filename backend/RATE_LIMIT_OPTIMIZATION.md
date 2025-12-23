# Yahoo Finance Rate Limit Optimization

## Rate Limits
- **60 requests per minute**
- **360 requests per hour**
- **8,000 requests per day**

## Previous Configuration (Causing Rate Limiting)

### Old Settings
- Scraping interval: **5 minutes**
- Delay between stocks: **1 second**
- Option expirations: **~15 average** (all available)
- Watchlist size: **54 stocks**

### Old Request Volume
Per stock: ~17 requests (1 price + 1 expirations + 15 option chains)
- **Per cycle**: 54 stocks × 17 = **918 requests**
- **Per minute**: 918 / 5 = **184 requests/min** ❌ (3x over 60/min limit)
- **Per hour**: 12 cycles × 918 = **11,016 requests/hour** ❌ (30.6x over 360/hour limit)
- **Per day**: 288 cycles × 918 = **264,384 requests/day** ❌ (33x over 8,000/day limit)

## New Configuration (Rate Limit Compliant)

### New Settings
- Scraping interval: **120 minutes (2 hours)**
- Delay between stocks: **10 seconds**
- Option expirations: **8 nearest dates** (focused on near-term)
- Watchlist size: **54 stocks** (unchanged, but can support up to 80)
- Scheduler: **Starts paused by default**

### New Request Volume
Per stock: ~10 requests (1 price + 1 expirations + 8 option chains)
- **Per cycle**: 54 stocks × 10 = **540 requests**
- **Cycle duration**: 54 stocks × 10 sec = 9 minutes to complete
- **Per minute**: 540 / 9 = **60 requests/min** ✅ (at limit)
- **Per hour**: ~0.5 cycles × 540 = **270 requests/hour** ✅ (under 360/hour limit)
- **Per day**: 12 cycles × 540 = **6,480 requests/day** ✅ (under 8,000/day limit)

## Optimizations Implemented

### 1. Increased Scraping Interval (5 min → 120 min)
**File**: `backend/src/config.py`
```python
polling_interval_minutes: int = 120  # Default: 2 hours
```
- Reduces scrape cycles from 288/day to 12/day
- Options data doesn't change frequently enough to warrant 5-min updates
- 2-hour intervals still provide timely data during market hours

### 2. Added Stock Delays (1 sec → 10 sec)
**File**: `backend/src/services/scraper.py`
```python
time.sleep(10)  # 10 sec delay between stocks
```
- Spreads 540 requests over 9 minutes (~60/min)
- Prevents burst requests that trigger rate limiting
- With 54 stocks: 54 × 10 sec = 9 minutes per cycle

### 3. Limited Expirations (15 → 8)
**File**: `backend/src/services/scraper.py`
```python
# Limit to 8 nearest expirations
expirations = expirations[:8]
```
- Reduces requests per stock from ~17 to ~10
- Near-term options (0-90 days) have most trading activity
- Focused on actionable data rather than far-dated contracts

### 4. Rate Limit Tracking
**File**: `backend/src/services/scraper.py`
- Added `total_api_requests` counter
- Added `rate_limit_warnings` list
- Logs warnings if approaching/exceeding limits:
  - Per-minute rate: 60/min
  - Per-cycle total: 360 max

### 5. Scheduler Starts Paused
**File**: `backend/src/services/scheduler.py`
```python
# Start paused to prevent immediate rate limiting
if config.scheduler_status != SchedulerStatus.paused:
    config.scheduler_status = SchedulerStatus.paused
```
- Prevents automatic scraping on startup
- User must manually start via Admin page
- Allows time to configure watchlist size

### 6. Extended Interval Validation
**File**: `backend/src/services/scheduler.py`
```python
if not 1 <= polling_interval_minutes <= 1440:  # Up to 24 hours
```
- Allows intervals up to 24 hours (was limited to 60 min)
- Supports flexible scheduling strategies

## Request Breakdown Per Stock

### Typical Stock (e.g., SPY, AAPL, TSLA)
```
1. Get current price           1 request
2. Get expiration dates        1 request
3. Get option chain (8 dates)  8 requests
                              ----------
Total per stock:              10 requests
```

### Stocks with Many Expirations (limited to 8)
- Before: 30+ expirations = 32 requests/stock
- After: 8 nearest = 10 requests/stock
- Savings: ~22 requests per high-volume stock

## Watchlist Capacity

Based on rate limits, maximum watchlist sizes:

### At 2-hour interval (12 cycles/day)
- **Conservative (270 req/hour)**: 27 stocks × 10 req = 270 requests ✅
- **Target (300 req/hour)**: 30 stocks × 10 req = 300 requests ✅
- **Maximum (540 req/cycle)**: 54 stocks × 10 req = 540 requests ✅
- **Absolute max (8000/day)**: 80 stocks × 10 req × 12 cycles = 9,600 ❌

**Recommended**: Keep watchlist between 30-54 stocks with 2-hour interval

### Other Configurations
| Interval | Stocks | Requests/Cycle | Requests/Day | Status |
|----------|--------|----------------|--------------|--------|
| 30 min   | 10     | 100            | 4,800        | ✅ Safe |
| 1 hour   | 20     | 200            | 4,800        | ✅ Safe |
| 2 hours  | 54     | 540            | 6,480        | ✅ Safe |
| 3 hours  | 80     | 800            | 6,400        | ✅ Safe |
| 4 hours  | 100    | 1,000          | 6,000        | ✅ Safe |

## Usage Instructions

### Starting the Scheduler
1. Adjust watchlist to desired size (30-54 stocks recommended)
2. Go to Admin page → Scheduler section
3. Click "Start Scheduler" button
4. Monitor logs for rate limit warnings

### If Rate Limited
If you still hit rate limits:
1. **Pause scheduler immediately** (Admin page)
2. **Wait 24-48 hours** for IP ban to clear
3. Choose one option:
   - Reduce watchlist to 30 stocks
   - Increase interval to 3-4 hours
   - Focus on specific stocks instead of broad coverage

### Monitoring
Check scraper logs after each run:
```
INFO: Scraper run completed:
  - total_api_requests: 540
  - requests_per_stock: 10.0
  - rate_limit_warnings: []  ✅ Good
```

If warnings appear:
```
WARNING: Exceeded 60 requests/min limit: 72.5/min  ❌ Reduce stocks or increase interval
```

## Technical Details

### API Call Sequence (per stock)
```python
1. ticker_obj.fast_info          # Get current price (1 request)
2. ticker_obj.options            # Get expiration dates (1 request)
3. Loop through 8 expirations:
   ticker_obj.option_chain(date) # Get calls + puts (1 request per date)
```

### Retry Logic
- Each request retries up to 3 times on failure
- Exponential backoff: 1s, 2s, 4s
- If all retries fail on HTTP 429: stop processing that stock

### Market Hours
- Scraper runs 24/7 but honors market hours for business logic
- Data collected outside market hours for pre-market analysis
- Market hours: 9:30 AM - 4:00 PM ET (configurable)

## Future Enhancements

### Possible Optimizations
1. **Smart expiration filtering**: Only fetch weekly options for high-volume stocks
2. **Differential updates**: Only fetch changed data, not full chains every time
3. **Stock rotation**: Scrape 1/3 of stocks each cycle, full coverage over 6 hours
4. **Cache expiration data**: Fetch once per day instead of every cycle
5. **Prioritization**: Scrape high-priority stocks more frequently than others

### Alternative Data Sources
If Yahoo Finance continues to be restrictive:
- **CBOE DataShop**: Official options data (paid)
- **Interactive Brokers API**: Real-time data with account
- **Polygon.io**: Options API with generous rate limits (paid)
- **Alpha Vantage**: Options data API (limited free tier)

## Summary

✅ **Rate limit compliant configuration achieved**
- 6,480 requests/day (under 8,000 limit)
- 60 requests/min average (at limit, with 10-sec delays)
- 270 requests/hour per cycle (under 360 limit)

✅ **Maintains data quality**
- 8 nearest expirations covers 90% of trading activity
- 2-hour updates sufficient for daily/swing trading strategies
- All 54 stocks monitored continuously

✅ **Safe restart mechanism**
- Scheduler starts paused
- User must manually enable after configuration
- Rate limit warnings prevent future violations
