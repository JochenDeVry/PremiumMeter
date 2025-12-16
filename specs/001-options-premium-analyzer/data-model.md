# Data Model: Options Premium Analyzer

**Feature**: 001-options-premium-analyzer | **Date**: 2025-12-15

## Entity-Relationship Diagram

```
┌─────────────────┐         ┌──────────────────────┐
│     Stock       │         │  HistoricalPremium   │
├─────────────────┤         │      Record          │
│ id (PK)         │◄────────┤ id (PK)              │
│ ticker (UK)     │    1:N  │ stock_id (FK)        │
│ company_name    │         │ option_type          │
│ current_price   │         │ strike_price         │
│ status          │         │ premium              │
│ date_added      │         │ expiration_date      │
└─────────────────┘         │ collection_timestamp │
                            │ delta                │
        ┌───────────────────┤ gamma                │
        │                   │ theta                │
        │                   │ vega                 │
        │                   │ implied_volatility   │
        │                   │ volume               │
        │                   │ open_interest        │
        │                   │ contract_status      │
        │                   └──────────────────────┘
        │
        │   ┌──────────────────────┐
        │   │   ScraperSchedule    │
        │   ├──────────────────────┤
        │   │ id (PK)              │
        │   │ scrape_time_utc      │
        │   │ timezone             │
        │   │ enabled              │
        │   │ excluded_days        │ (JSON array)
        │   │ last_run             │
        │   │ next_run             │
        │   │ status               │
        │   └──────────────────────┘
        │
        │   ┌──────────────────────┐
        │   │   Watchlist          │
        │   ├──────────────────────┤
        │   │ id (PK)              │
        └───┤ stock_id (FK)        │
            │ monitoring_status    │
            │ date_added           │
            │ date_removed         │
            └──────────────────────┘

Phase 2 Entities (Not in MVP):

┌─────────────────┐         ┌──────────────────────┐
│     User        │         │       Role           │
├─────────────────┤         ├──────────────────────┤
│ id (PK)         │    N:1  │ id (PK)              │
│ username (UK)   │─────────►│ name (UK)            │
│ email (UK)      │         │ permissions          │ (JSON array)
│ password_hash   │         └──────────────────────┘
│ role_id (FK)    │
│ account_status  │
│ created_at      │
│ last_login      │
└─────────────────┘
```

## Core Entities (MVP)

### Stock

Represents a US publicly traded company that can have options contracts.

**Attributes**:
- `id` (Integer, Primary Key): Auto-incrementing unique identifier
- `ticker` (String[10], Unique, Not Null): Stock ticker symbol (e.g., "AAPL", "META")
- `company_name` (String[200]): Full company name (e.g., "Apple Inc.")
- `current_price` (Decimal[10,2], Nullable): Most recent stock price from scraper
- `status` (String[20], Default='active'): Stock monitoring status ('active', 'delisted', 'inactive')
- `date_added` (DateTime, Default=now()): When stock was added to system

**Indexes**:
- Primary key on `id`
- Unique index on `ticker`
- Index on `status` for active stock queries

**Validation Rules**:
- Ticker must be uppercase alphanumeric, 1-10 characters
- Current price must be positive if present
- Status must be one of: 'active', 'delisted', 'inactive'

**Relationships**:
- One-to-Many with HistoricalPremiumRecord (one stock has many historical records)
- One-to-One with Watchlist (one stock can be in watchlist once)

**Business Logic**:
- Ticker validation via yfinance before insertion
- Current price updated on each successful scrape
- Status changes to 'delisted' if scraper detects ticker no longer exists

---

### HistoricalPremiumRecord

Represents a point-in-time snapshot of an options contract premium and Greeks.

**Attributes**:
- `id` (BigInteger, Primary Key): Auto-incrementing unique identifier
- `stock_id` (Integer, Foreign Key → Stock.id, Not Null): Reference to underlying stock
- `option_type` (String[10], Not Null): 'call' or 'put'
- `strike_price` (Decimal[10,2], Not Null): Option strike price
- `premium` (Decimal[10,2], Not Null): Option premium (last traded price)
- `stock_price_at_collection` (Decimal[10,2], Not Null): Current stock price when premium was collected (critical for moneyness analysis)
- `expiration_date` (Date, Not Null): Contract expiration date
- `collection_timestamp` (Timestamp with timezone, Not Null): When data was scraped
- `delta` (Decimal[8,6], Nullable): Delta Greek (rate of change relative to stock price)
- `gamma` (Decimal[8,6], Nullable): Gamma Greek (rate of change of delta)
- `theta` (Decimal[8,6], Nullable): Theta Greek (time decay per day)
- `vega` (Decimal[8,6], Nullable): Vega Greek (sensitivity to volatility)
- `implied_volatility` (Decimal[6,4], Nullable): Implied volatility (annualized)
- `volume` (Integer, Nullable): Trading volume for the day
- `open_interest` (Integer, Nullable): Open interest (outstanding contracts)
- `contract_status` (String[20], Default='active'): 'active' or 'expired'

**Indexes**:
- Primary key on `id`
- Foreign key index on `stock_id`
- Composite index on `(stock_id, option_type, strike_price, expiration_date)` for query performance
- Index on `collection_timestamp` (TimescaleDB hypertable partition key)
- Index on `contract_status`

**Validation Rules**:
- Option type must be 'call' or 'put'
- Strike price, premium, and stock_price_at_collection must be positive
- Expiration date must be future date at time of insertion
- Delta range: -1.0 to 1.0 (calls: 0 to 1, puts: -1 to 0)
- Gamma, theta, vega must be reasonable ranges (validated in application layer)
- Implied volatility must be between 0 and 5.0 (0% to 500%)

**Relationships**:
- Many-to-One with Stock (many records belong to one stock)

**Business Logic**:
- TimescaleDB hypertable partitioned by `collection_timestamp` (daily chunks for intra-day polling)
- Stock price captured at collection time enables moneyness analysis (In-The-Money, At-The-Money, Out-Of-The-Money)
- Greeks populated from Yahoo Finance if available, otherwise calculated via Black-Scholes
- Contract status changes to 'expired' when `expiration_date` < current date (scheduled job)
- Continuous aggregate materialized view for daily min/max/avg premiums with stock price ranges

**Query Patterns**:
```sql
-- User Story 1: Query historical premiums for specific criteria
SELECT 
    collection_timestamp::date as date,
    MIN(premium) as min_premium,
    MAX(premium) as max_premium,
    AVG(premium) as avg_premium
FROM historical_premium_records
WHERE stock_id = (SELECT id FROM stock WHERE ticker = 'META')
  AND option_type = 'put'
  AND strike_price = 635.00
  AND expiration_date - collection_timestamp::date BETWEEN 13 AND 15  -- 2 weeks ±1 day
  AND collection_timestamp > NOW() - INTERVAL '90 days'
GROUP BY date
ORDER BY date DESC;

-- Exact strike match
WHERE strike_price = 635.00

-- Percentage range match (±5%)
WHERE strike_price BETWEEN 603.25 AND 666.75

-- N nearest strikes (subquery approach)
WHERE id IN (
    SELECT id FROM historical_premium_records
    WHERE stock_id = ... AND strike_price > 635.00
    ORDER BY strike_price ASC LIMIT 3
  UNION
    SELECT id FROM historical_premium_records
    WHERE stock_id = ... AND strike_price < 635.00
    ORDER BY strike_price DESC LIMIT 3
)
```

---

### Watchlist

Represents the collection of stocks actively monitored for options data scraping.

**Attributes**:
- `id` (Integer, Primary Key): Auto-incrementing unique identifier
- `stock_id` (Integer, Foreign Key → Stock.id, Unique, Not Null): Reference to stock
- `monitoring_status` (String[20], Default='active'): 'active' or 'paused'
- `date_added` (DateTime, Default=now()): When stock was added to watchlist
- `date_removed` (DateTime, Nullable): When stock was removed (soft delete)

**Indexes**:
- Primary key on `id`
- Unique index on `stock_id`
- Index on `monitoring_status`

**Validation Rules**:
- Stock must exist in Stock table before adding to watchlist
- Monitoring status must be 'active' or 'paused'
- Date removed must be >= date_added if present

**Relationships**:
- Many-to-One with Stock (many watchlist entries can reference one stock - but unique constraint enforces 1:1)

**Business Logic**:
- Initial seed: 54 stocks added via Alembic migration
- Removing stock from watchlist sets `date_removed` (soft delete) and `monitoring_status='paused'`
- Scraper only processes stocks where `monitoring_status='active'` AND `date_removed IS NULL`
- Historical data retained even when stock removed (FR-012)

---

### ScraperSchedule

Represents the configuration for automated options data polling with intra-day frequency.

**Attributes**:
- `id` (Integer, Primary Key): Auto-incrementing unique identifier (singleton - only one row)
- `polling_interval_minutes` (Integer, Not Null, Default=5): Frequency of polling in minutes (1-60)
- `market_hours_start` (Time, Not Null, Default='09:30:00'): Market open time (local to timezone)
- `market_hours_end` (Time, Not Null, Default='16:00:00'): Market close time (local to timezone)
- `timezone` (String[50], Not Null, Default='America/New_York'): Timezone name for market hours (pytz format)
- `enabled` (Boolean, Default=true): Whether polling is active
- `excluded_days` (JSON Array, Nullable): Days to skip, e.g., `["saturday", "sunday", "2025-12-25"]`
- `last_run` (Timestamp with timezone, Nullable): When last poll completed
- `next_run` (Timestamp with timezone, Nullable): Calculated next poll time
- `status` (String[20], Default='idle'): 'idle', 'running', 'paused', 'error'

**Indexes**:
- Primary key on `id`
- Index on `enabled`
- Index on `next_run` for scheduler queries
- Unique constraint ensuring only one row (application-level enforcement)

**Validation Rules**:
- Polling interval must be between 1 and 60 minutes
- Market hours start must be before market hours end
- Timezone must be valid pytz timezone string
- Excluded days format: day names (lowercase) or ISO dates (YYYY-MM-DD)
- Status must be one of: 'idle', 'running', 'paused', 'error'

**Relationships**:
- Standalone table (no foreign keys)

**Business Logic**:
- APScheduler reads this configuration to set IntervalTrigger with polling_interval_minutes
- Polling only occurs during market_hours_start to market_hours_end window (checked before each execution)
- Admin UI updates this table; APScheduler reschedules job dynamically without restart
- `next_run` calculated by APScheduler based on polling_interval_minutes + market hours + timezone + excluded_days
- Status changes: 'idle' → 'running' (poll starts) → 'idle' (success) or 'error' (failure)
- Pause sets status='paused', prevents execution until resumed

---

## Phase 2 Entities (Not in MVP)

### User

Represents an application user with authentication credentials.

**Attributes**:
- `id` (Integer, Primary Key): Auto-incrementing unique identifier
- `username` (String[50], Unique, Not Null): Login username
- `email` (String[100], Unique, Not Null): User email address
- `password_hash` (String[255], Not Null): Bcrypt/Argon2 hashed password
- `role_id` (Integer, Foreign Key → Role.id, Not Null): User's role
- `account_status` (String[20], Default='active'): 'active', 'inactive', 'locked'
- `created_at` (Timestamp, Default=now()): Account creation timestamp
- `last_login` (Timestamp, Nullable): Most recent login timestamp

**Indexes**:
- Primary key on `id`
- Unique index on `username`
- Unique index on `email`
- Foreign key index on `role_id`

**Validation Rules**:
- Username: 3-50 alphanumeric characters + underscore
- Email: valid email format (RFC 5322)
- Password hash: bcrypt $2b$ or Argon2 $argon2id$ prefix
- Account status: 'active', 'inactive', 'locked'

**Relationships**:
- Many-to-One with Role (many users have one role)

---

### Role

Represents a user permission level (Admin or Viewer).

**Attributes**:
- `id` (Integer, Primary Key): Auto-incrementing unique identifier
- `name` (String[50], Unique, Not Null): Role name ('Admin' or 'Viewer')
- `permissions` (JSON Array, Not Null): List of allowed actions, e.g., `["query_data", "view_charts", "manage_watchlist", "configure_scraper", "manage_users"]`

**Indexes**:
- Primary key on `id`
- Unique index on `name`

**Validation Rules**:
- Name must be 'Admin' or 'Viewer'
- Permissions must be array of valid permission strings

**Relationships**:
- One-to-Many with User (one role has many users)

**Seed Data**:
```sql
INSERT INTO role (name, permissions) VALUES
('Admin', '["query_data", "view_charts", "manage_watchlist", "configure_scraper", "manage_users"]'),
('Viewer', '["query_data", "view_charts"]');
```

---

## Database Schema (SQL)

### PostgreSQL + TimescaleDB Schema

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Stock table
CREATE TABLE stock (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    company_name VARCHAR(200),
    current_price DECIMAL(10,2) CHECK (current_price > 0),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'delisted', 'inactive')),
    date_added TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_stock_status ON stock(status);

-- Historical premium records (TimescaleDB hypertable)
CREATE TABLE historical_premium_records (
    id BIGSERIAL PRIMARY KEY,
    stock_id INTEGER NOT NULL REFERENCES stock(id) ON DELETE RESTRICT,
    option_type VARCHAR(10) NOT NULL CHECK (option_type IN ('call', 'put')),
    strike_price DECIMAL(10,2) NOT NULL CHECK (strike_price > 0),
    premium DECIMAL(10,2) NOT NULL CHECK (premium >= 0),
    expiration_date DATE NOT NULL,
    collection_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    delta DECIMAL(8,6) CHECK (delta BETWEEN -1 AND 1),
    gamma DECIMAL(8,6),
    theta DECIMAL(8,6),
    vega DECIMAL(8,6),
    implied_volatility DECIMAL(6,4) CHECK (implied_volatility BETWEEN 0 AND 5),
    volume INTEGER CHECK (volume >= 0),
    open_interest INTEGER CHECK (open_interest >= 0),
    contract_status VARCHAR(20) DEFAULT 'active' CHECK (contract_status IN ('active', 'expired'))
);

-- Convert to hypertable (partition by collection_timestamp)
SELECT create_hypertable('historical_premium_records', 'collection_timestamp', chunk_time_interval => INTERVAL '1 month');

-- Indexes for query performance
CREATE INDEX idx_hpr_stock_id ON historical_premium_records(stock_id);
CREATE INDEX idx_hpr_query_pattern ON historical_premium_records(stock_id, option_type, strike_price, expiration_date);
CREATE INDEX idx_hpr_status ON historical_premium_records(contract_status);

-- Compression policy for old data (compress data older than 90 days)
SELECT add_compression_policy('historical_premium_records', INTERVAL '90 days');

-- Continuous aggregate for daily summary
CREATE MATERIALIZED VIEW daily_premium_summary
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', collection_timestamp) AS day,
    stock_id,
    option_type,
    strike_price,
    expiration_date,
    MIN(premium) as min_premium,
    MAX(premium) as max_premium,
    AVG(premium) as avg_premium,
    COUNT(*) as data_points
FROM historical_premium_records
GROUP BY day, stock_id, option_type, strike_price, expiration_date
WITH NO DATA;

-- Refresh policy for continuous aggregate (refresh last 7 days every hour)
SELECT add_continuous_aggregate_policy('daily_premium_summary',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- Watchlist table
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER UNIQUE NOT NULL REFERENCES stock(id) ON DELETE RESTRICT,
    monitoring_status VARCHAR(20) DEFAULT 'active' CHECK (monitoring_status IN ('active', 'paused')),
    date_added TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    date_removed TIMESTAMP WITH TIME ZONE,
    CHECK (date_removed IS NULL OR date_removed >= date_added)
);

CREATE INDEX idx_watchlist_status ON watchlist(monitoring_status);

-- Scraper schedule table (singleton)
CREATE TABLE scraper_schedule (
    id SERIAL PRIMARY KEY,
    scrape_time_utc TIME NOT NULL,
    timezone VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    excluded_days JSONB,
    last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'idle' CHECK (status IN ('idle', 'running', 'error'))
);

-- Ensure singleton (only one row allowed)
CREATE UNIQUE INDEX idx_scraper_schedule_singleton ON scraper_schedule((id IS NOT NULL));

-- Phase 2: User table (not created in MVP)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE RESTRICT,
    account_status VARCHAR(20) DEFAULT 'active' CHECK (account_status IN ('active', 'inactive', 'locked')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_role ON users(role_id);

-- Phase 2: Role table (not created in MVP)
CREATE TABLE role (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL CHECK (name IN ('Admin', 'Viewer')),
    permissions JSONB NOT NULL
);
```

---

## Data Migration Strategy

### Initial Setup (Alembic Migration)

1. **Migration 001**: Create core tables (stock, historical_premium_records, watchlist, scraper_schedule)
2. **Migration 002**: Enable TimescaleDB extension and create hypertable
3. **Migration 003**: Seed 54-stock initial watchlist
4. **Migration 004**: Create continuous aggregate views and policies
5. **Migration 005** (Phase 2): Create user/role tables

### Seed Data Scripts

**54-Stock Watchlist Seed**:
```python
# Alembic migration: versions/003_seed_watchlist.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Insert 54 stocks
    stocks = [
        ('ADBE', 'Adobe Inc.'), ('AMD', 'Advanced Micro Devices Inc.'),
        ('BABA', 'Alibaba Group Holding Ltd - ADR'), ('GOOGL', 'Alphabet Inc. Class A'),
        ('GOOG', 'Alphabet Inc. Class C'), ('AMZN', 'Amazon.com Inc.'),
        ('AAL', 'American Airlines Group Inc.'), ('AAPL', 'Apple Inc.'),
        # ... (all 54 stocks)
    ]
    
    conn = op.get_bind()
    for ticker, company_name in stocks:
        # Insert stock
        result = conn.execute(
            sa.text("INSERT INTO stock (ticker, company_name, status) VALUES (:ticker, :company_name, 'active') ON CONFLICT (ticker) DO NOTHING RETURNING id"),
            {"ticker": ticker, "company_name": company_name}
        )
        stock_id = result.scalar()
        
        # Add to watchlist
        if stock_id:
            conn.execute(
                sa.text("INSERT INTO watchlist (stock_id, monitoring_status) VALUES (:stock_id, 'active')"),
                {"stock_id": stock_id}
            )

def downgrade():
    op.execute("DELETE FROM watchlist")
    op.execute("DELETE FROM stock WHERE ticker IN ('ADBE', 'AMD', ...)")  # All 54 tickers
```

**Default Scraper Schedule**:
```python
# Alembic migration: versions/003_seed_watchlist.py (continued)
def upgrade():
    # ... (watchlist seed above)
    
    # Insert default scraper schedule (5:00 PM ET daily, skip weekends)
    conn.execute(
        sa.text("""
            INSERT INTO scraper_schedule (scrape_time_utc, timezone, enabled, excluded_days)
            VALUES ('22:00:00', 'America/New_York', TRUE, '["saturday", "sunday"]')
        """)
    )
```

---

## Data Lifecycle Management

### Data Retention
- **Active contracts**: Keep all data indefinitely (historical value)
- **Expired contracts**: Compress after 90 days (TimescaleDB compression policy)
- **Old data archival**: Consider moving data older than 2 years to cold storage (future optimization)

### Data Purging
- **Scraper logs**: Delete entries older than 30 days
- **User sessions** (Phase 2): Delete expired sessions older than 7 days
- **Audit logs** (Phase 2+): Retain for 1 year minimum for compliance

### Backup Strategy
- **Daily backups**: Full PostgreSQL dump via pg_dump
- **Continuous archiving**: Write-Ahead Log (WAL) archiving for point-in-time recovery
- **Retention**: Keep daily backups for 30 days, weekly backups for 1 year

---

## Performance Optimization

### Query Optimization
- Use continuous aggregates for pre-computed daily summaries (avoid scanning millions of rows)
- Partition historical_premium_records by month (automatic with TimescaleDB hypertable)
- Index on common query patterns: (stock_id, option_type, strike_price, expiration_date)

### Write Optimization
- Batch insert scraper results (insert 100+ contracts per transaction)
- Use `COPY` command for bulk inserts (faster than individual INSERTs)
- Disable indexes during bulk load, rebuild after (if importing historical data)

### Storage Optimization
- Enable TimescaleDB compression for data older than 90 days (10x compression ratio typical)
- Use DECIMAL for financial data (exact precision) vs FLOAT (avoid rounding errors)
- JSONB for excluded_days (flexible schema, GIN index support if needed)

### Monitoring Queries
```sql
-- Check hypertable chunk sizes
SELECT * FROM timescaledb_information.chunks WHERE hypertable_name = 'historical_premium_records';

-- Check compression ratio
SELECT * FROM timescaledb_information.compression_settings WHERE hypertable_name = 'historical_premium_records';

-- Check continuous aggregate refresh lag
SELECT * FROM timescaledb_information.continuous_aggregate_stats WHERE view_name = 'daily_premium_summary';
```
