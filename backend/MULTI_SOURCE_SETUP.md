# Multi-Source Stock Price Configuration

The system now rotates between multiple data sources to avoid rate limiting:

## Data Sources (in priority order):

1. **Yahoo Finance** (yfinance) - No API key required
2. **Alpha Vantage** - Optional, requires free API key
3. **Finnhub** - Optional, requires free API key
4. **Database** - Final fallback to cached prices

## Setup (Optional - for better reliability):

### Get Free API Keys:

1. **Alpha Vantage** (25 requests/day free)
   - Visit: https://www.alphavantage.co/support/#api-key
   - Sign up and get your free API key
   
2. **Finnhub** (60 calls/minute free)
   - Visit: https://finnhub.io/register
   - Sign up and get your free API key

### Configure API Keys:

Create a `.env` file in the `backend/` directory:

```bash
# Optional: Add your API keys for alternative sources
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
FINNHUB_API_KEY=your_finnhub_key_here
```

**Note**: The system works without API keys (using Yahoo Finance only), but adding alternative sources provides better reliability when Yahoo blocks requests.

## How It Works:

1. **Cache First** - Checks 10-minute cache
2. **Source Rotation** - Tries available sources in order
3. **Health Tracking** - Automatically skips blocked sources
4. **Exponential Backoff** - Cooldown increases with repeated failures (30min → 1hr → 2hr → 4hr)
5. **Database Fallback** - Uses cached prices if all sources fail

## Current Status:

The backend will log which source is used for each request:
- `Fetched price for AAPL from yahoo_finance`
- `Fetched price for META from alpha_vantage`
- `All sources failed, using database fallback`

Check the backend logs to see source rotation in action!
