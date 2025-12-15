# Research: Options Premium Analyzer

**Feature**: 001-options-premium-analyzer | **Date**: 2025-12-15

## Research Questions Resolved

### 1. Yahoo Finance Integration Approach

**Decision**: Use `yfinance` Python library with error handling and fallback strategies

**Rationale**:
- **yfinance library benefits**: Actively maintained, wraps Yahoo Finance in Pythonic API, handles rate limiting, provides options chain data directly
- **Alternative considered**: Direct web scraping via BeautifulSoup/Selenium - rejected due to fragility (HTML structure changes break scrapers), higher maintenance burden, potential ToS violations
- **Risk mitigation**: Implement robust error handling, logging for structure changes, monitor yfinance GitHub for breaking changes, design scraper service with abstraction layer to allow future data source swaps

**Implementation notes**:
```python
import yfinance as yf

ticker = yf.Ticker("AAPL")
# Get all expiration dates
expirations = ticker.options  # Returns tuple of expiration date strings

# Get options chain for specific expiration
options_chain = ticker.option_chain('2025-12-19')
calls = options_chain.calls  # DataFrame with call options
puts = options_chain.puts    # DataFrame with put options

# Available fields: strike, lastPrice, bid, ask, volume, openInterest,
# impliedVolatility, inTheMoney, contractSymbol, lastTradeDate
```

### 2. Time-Series Database Optimization

**Decision**: PostgreSQL 15+ with TimescaleDB extension for hypertables

**Rationale**:
- **TimescaleDB benefits**: Automatic partitioning by time, time_bucket() for aggregations, continuous aggregates for pre-computed summaries, compression for old data, compatible with standard PostgreSQL (no migration needed)
- **Alternatives considered**:
  - Pure PostgreSQL with manual partitioning - rejected due to complexity of maintaining partition boundaries
  - InfluxDB - rejected due to limited relational query support (need JOINs for stocks/contracts)
  - MongoDB with time-series collections - rejected due to weaker transaction guarantees, less mature Python ecosystem
- **Query optimization**: Create hypertable on `historical_premium_records` partitioned by `collection_timestamp`, indexes on (ticker, strike, expiration_date), continuous aggregate for daily min/max/avg premiums

**Implementation notes**:
```sql
-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create hypertable (automatic time-based partitioning)
SELECT create_hypertable('historical_premium_records', 'collection_timestamp');

-- Create indexes for query patterns
CREATE INDEX idx_ticker_strike_exp ON historical_premium_records(ticker, strike_price, expiration_date);
CREATE INDEX idx_option_type ON historical_premium_records(option_type, collection_timestamp DESC);

-- Continuous aggregate for daily summaries (pre-computed for performance)
CREATE MATERIALIZED VIEW daily_premium_summary
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', collection_timestamp) AS day,
       ticker,
       option_type,
       strike_price,
       expiration_date,
       MIN(premium) as min_premium,
       MAX(premium) as max_premium,
       AVG(premium) as avg_premium,
       COUNT(*) as data_points
FROM historical_premium_records
GROUP BY day, ticker, option_type, strike_price, expiration_date;
```

### 3. Scheduler Implementation (Timezone-Aware)

**Decision**: APScheduler with CronTrigger and pytz for timezone handling

**Rationale**:
- **APScheduler benefits**: Lightweight, supports cron expressions, timezone-aware triggers, persistent job store (survives restarts), pause/resume capabilities, Python-native (integrates with FastAPI)
- **Alternatives considered**:
  - Celery Beat - rejected due to heavyweight (requires Redis/RabbitMQ broker), overkill for single-node deployment
  - System cron - rejected due to lack of dynamic configuration, no timezone awareness, can't pause/resume programmatically
- **DST handling**: pytz automatically handles daylight saving time transitions, triggers adjust without manual intervention

**Implementation notes**:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

scheduler = AsyncIOScheduler()

# Schedule daily scrape at 5:00 PM Eastern Time (handles DST automatically)
scheduler.add_job(
    func=scrape_all_stocks,
    trigger=CronTrigger(hour=17, minute=0, timezone=pytz.timezone('America/New_York')),
    id='daily_scrape',
    replace_existing=True,
    name='Daily Options Scrape'
)

# Pause/resume programmatically
scheduler.pause_job('daily_scrape')
scheduler.resume_job('daily_scrape')

# Exclude specific days (modify trigger)
scheduler.reschedule_job(
    'daily_scrape',
    trigger=CronTrigger(hour=17, minute=0, day_of_week='mon-fri', timezone=pytz.timezone('America/New_York'))
)
```

### 4. Black-Scholes Greeks Calculation

**Decision**: Implement Black-Scholes model using scipy.stats for Greeks calculation

**Rationale**:
- **scipy benefits**: Well-tested statistical functions, norm.cdf() for cumulative normal distribution, vectorized for batch calculations, NumPy integration for performance
- **Alternatives considered**:
  - QuantLib library - rejected due to heavyweight (C++ bindings), complex installation, overkill for basic Greeks
  - Manual implementation - rejected due to numerical precision concerns, reinventing tested code
- **Required inputs**: Stock price (current from yfinance), strike price (contract data), time to expiry (days until expiration_date), risk-free rate (fetch from Fred API or hardcode ~4-5%), implied volatility (from Yahoo Finance or calculate from historical)

**Implementation notes**:
```python
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta

def calculate_greeks(S, K, T, r, sigma, option_type='call'):
    """
    S: Current stock price
    K: Strike price
    T: Time to expiration (years)
    r: Risk-free rate (annualized)
    sigma: Implied volatility (annualized)
    option_type: 'call' or 'put'
    
    Returns: dict with delta, gamma, theta, vega
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        delta = norm.cdf(d1)
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                 - r * K * np.exp(-r * T) * norm.cdf(d2))
    else:  # put
        delta = -norm.cdf(-d1)
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                 + r * K * np.exp(-r * T) * norm.cdf(-d2))
    
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T)
    
    return {
        'delta': delta,
        'gamma': gamma,
        'theta': theta / 365,  # Daily theta
        'vega': vega / 100     # Vega per 1% volatility change
    }

# Example usage
days_to_expiry = (expiration_date - datetime.now().date()).days
T = days_to_expiry / 365.0
greeks = calculate_greeks(S=635.50, K=635, T=T, r=0.045, sigma=0.25, option_type='put')
```

### 5. Strike Price Matching Query Strategies

**Decision**: Three query modes implemented as SQLAlchemy filters with parameterized queries

**Rationale**:
- **Exact strike**: Direct equality filter `WHERE strike_price = :strike`
- **Percentage range**: Calculated bounds `WHERE strike_price BETWEEN :lower AND :upper` where `lower = strike * (1 - pct/100)`, `upper = strike * (1 + pct/100)`
- **N nearest strikes**: Subquery with `ORDER BY ABS(strike_price - :target) LIMIT :n` for above/below, UNION results
- **SQL injection prevention**: SQLAlchemy parameterized queries prevent injection, Pydantic validates input types (float for strike, int for count)

**Implementation notes**:
```python
from sqlalchemy import and_, or_, func

# Exact strike
query = session.query(HistoricalPremiumRecord).filter(
    HistoricalPremiumRecord.strike_price == strike
)

# Percentage range (±5%)
lower = strike * 0.95
upper = strike * 1.05
query = session.query(HistoricalPremiumRecord).filter(
    and_(
        HistoricalPremiumRecord.strike_price >= lower,
        HistoricalPremiumRecord.strike_price <= upper
    )
)

# N nearest (3 above, 3 below)
above = session.query(HistoricalPremiumRecord).filter(
    HistoricalPremiumRecord.strike_price > strike
).order_by(HistoricalPremiumRecord.strike_price.asc()).limit(3)

below = session.query(HistoricalPremiumRecord).filter(
    HistoricalPremiumRecord.strike_price < strike
).order_by(HistoricalPremiumRecord.strike_price.desc()).limit(3)

query = above.union(below)
```

### 6. Frontend Visualization Library

**Decision**: Plotly.js with React wrapper (react-plotly.js) for 3D interactive charts

**Rationale**:
- **Plotly.js benefits**: Native 3D surface plots, rotation/zoom/pan interactions, responsive resizing, export to PNG/SVG, WebGL acceleration for large datasets, TypeScript type definitions available
- **Alternatives considered**:
  - Three.js + D3.js - rejected due to custom implementation complexity, no built-in chart types
  - Chart.js - rejected due to limited 3D support (primarily 2D charts)
  - Recharts - rejected due to no native 3D support
- **2D fallback**: Plotly also provides 2D time-series, heatmaps, scatter plots - single library for all chart types

**Implementation notes**:
```tsx
import Plot from 'react-plotly.js';

const Chart3D = ({ data }) => {
  const plotData = [{
    type: 'surface',
    x: data.strikePrices,      // X-axis: strike prices
    y: data.durationsInDays,   // Y-axis: days to expiry
    z: data.premiumGrid,       // Z-axis: premium values (2D array)
    colorscale: 'Viridis',
    hovertemplate: 'Strike: %{x}<br>Duration: %{y} days<br>Premium: $%{z}<extra></extra>'
  }];
  
  const layout = {
    scene: {
      xaxis: { title: 'Strike Price' },
      yaxis: { title: 'Days to Expiry' },
      zaxis: { title: 'Premium ($)' }
    },
    hovermode: 'closest'
  };
  
  return <Plot data={plotData} layout={layout} />;
};
```

### 7. Initial Watchlist Seeding Strategy

**Decision**: Database migration with seed data for 54-stock watchlist

**Rationale**:
- **Migration approach**: Alembic migration creates `watchlist` table and inserts 54 ticker rows with status='active', ensures idempotency (ON CONFLICT DO NOTHING)
- **Alternatives considered**:
  - Hardcoded Python list - rejected due to no persistence across restarts
  - Configuration file (YAML/JSON) - rejected due to manual database sync required
- **Post-installation customization**: Admin UI modifies watchlist table directly, no special handling needed

**Implementation notes**:
```python
# Alembic migration: versions/xxxx_seed_initial_watchlist.py
from alembic import op
import sqlalchemy as sa
from datetime import datetime

def upgrade():
    # Create watchlist table
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('ticker', sa.String(10), unique=True, nullable=False),
        sa.Column('company_name', sa.String(200)),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('date_added', sa.DateTime, default=datetime.utcnow)
    )
    
    # Seed 54 stocks
    tickers = [
        ('ADBE', 'Adobe Inc.'),
        ('AMD', 'Advanced Micro Devices Inc.'),
        ('BABA', 'Alibaba Group Holding Ltd - ADR'),
        # ... (all 54 stocks from spec)
        ('WFBR', 'WhiteFiber Inc.')
    ]
    
    op.bulk_insert(
        sa.table('watchlist',
            sa.column('ticker', sa.String),
            sa.column('company_name', sa.String),
            sa.column('status', sa.String)
        ),
        [{'ticker': t, 'company_name': c, 'status': 'active'} for t, c in tickers]
    )
```

### 8. HTTPS Deployment and Security

**Decision**: Let's Encrypt SSL certificates with Nginx reverse proxy, FastAPI security middleware

**Rationale**:
- **Let's Encrypt benefits**: Free automated SSL certificates, auto-renewal via certbot, widely trusted CA, supports wildcard certificates
- **Nginx reverse proxy**: Terminates SSL, serves static frontend files, proxies API requests to FastAPI backend, handles compression/caching
- **FastAPI security**: CORSMiddleware for cross-origin requests, Pydantic validation prevents type-based attacks, SQLAlchemy parameterized queries prevent SQL injection, Jinja2 auto-escaping prevents XSS

**Implementation notes**:
```nginx
# /etc/nginx/sites-available/premium-meter
server {
    listen 443 ssl http2;
    server_name premiummeter.com;
    
    ssl_certificate /etc/letsencrypt/live/premiummeter.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/premiummeter.com/privkey.pem;
    
    # Frontend static files
    location / {
        root /var/www/premium-meter/frontend/build;
        try_files $uri /index.html;
    }
    
    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name premiummeter.com;
    return 301 https://$server_name$request_uri;
}
```

```python
# FastAPI security configuration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# CORS for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://premiummeter.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Prevent host header attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["premiummeter.com", "www.premiummeter.com"]
)
```

## Best Practices Summary

### Data Scraping
- Use yfinance library for Yahoo Finance access
- Implement exponential backoff for rate limit errors
- Log all scraping failures with ticker, timestamp, error message
- Store raw responses temporarily for debugging structure changes

### Database Design
- TimescaleDB hypertables for time-series premium data
- Continuous aggregates for pre-computed daily summaries
- Indexes on common query patterns (ticker, strike, expiration)
- Compression policy for data older than 90 days

### API Design
- RESTful endpoints with clear resource naming (/api/premium/query, /api/watchlist)
- Pydantic models for request/response validation
- Async endpoints for I/O-bound operations (database queries)
- Rate limiting (optional Phase 2) to prevent abuse

### Frontend Performance
- Lazy load Plotly.js (code splitting) to reduce initial bundle size
- Debounce user input for query form (500ms delay before API call)
- Cache query results in React state to avoid re-fetching on chart type switch
- Virtualize large result tables with react-window

### Security Hardening
- HTTPS-only deployment (redirect HTTP → HTTPS)
- Input validation via Pydantic (type checking, range validation)
- Parameterized SQL queries (SQLAlchemy ORM prevents injection)
- CSP headers to prevent XSS (Content-Security-Policy)
- Secure session cookies for Phase 2 authentication (HttpOnly, Secure, SameSite)

### Testing Strategy (Optional - not required in MVP spec)
- Unit tests for Greeks calculation (verify against known values)
- Integration tests for API endpoints (test query matching modes)
- Mock yfinance responses for scraper tests (avoid live API calls)
- End-to-end tests for critical user flows (query → visualize)

## Technology Integration Patterns

### Backend Stack Integration
```
FastAPI (web framework)
  ├─> SQLAlchemy (ORM) → PostgreSQL/TimescaleDB
  ├─> APScheduler (background jobs) → scraper service
  ├─> yfinance (data collection) → Yahoo Finance API
  ├─> scipy (calculations) → Black-Scholes Greeks
  └─> Pydantic (validation) → request/response schemas
```

### Frontend Stack Integration
```
React (UI framework)
  ├─> react-plotly.js (charts) → Plotly.js (3D visualization)
  ├─> axios (HTTP client) → FastAPI backend
  ├─> TypeScript (type safety) → compile-time validation
  └─> React Router (navigation) → SPA routing
```

### Deployment Stack Integration
```
Docker Compose (orchestration)
  ├─> Backend container (FastAPI + Python 3.11)
  ├─> Frontend container (Nginx + React build)
  ├─> PostgreSQL container (with TimescaleDB extension)
  └─> Certbot container (SSL certificate renewal)
```

## Phase 2 Authentication Preparation

While MVP is single-user without authentication, the architecture prepares for Phase 2 multi-user implementation:

**Database Schema Additions**:
- `users` table: id, username, email, password_hash (bcrypt), role_id, status, created_at, last_login
- `roles` table: id, name (Admin/Viewer), permissions (JSON array)
- Foreign keys: watchlist.created_by_user_id, scraper_schedule.modified_by_user_id

**API Endpoint Structure**:
- Endpoints already structured for permission checks: `/api/admin/watchlist`, `/api/admin/scheduler`
- Placeholder for authentication middleware: `@require_auth` decorator (no-op in MVP, enforces login in Phase 2)
- JWT token support prepared: FastAPI-JWT library integration point identified

**Frontend Component Design**:
- Conditional rendering structure: `{isAdmin && <WatchlistManager />}`
- Auth context provider prepared: `AuthContext` with `user` and `role` state (hardcoded Admin in MVP)
- Login page component scaffolded (not routed in MVP)

**Migration Path**:
- Add authentication tables via Alembic migration
- Enable authentication middleware (uncomment decorators)
- Update frontend to check `user.role` for feature visibility
- No refactoring of core business logic required
