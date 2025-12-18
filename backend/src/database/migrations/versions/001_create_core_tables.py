"""001_create_core_tables

Revision ID: 001_create_core
Revises: 
Create Date: 2025-12-16 21:00:00.000000

Migration: Create core database tables
- Stock
- HistoricalPremiumRecord
- Watchlist
- ScraperSchedule
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '001_create_core'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Create enums using raw SQL
    conn.execute(text("""
        CREATE TYPE stock_status AS ENUM ('active', 'delisted', 'inactive');
        CREATE TYPE option_type AS ENUM ('call', 'put');
        CREATE TYPE contract_status AS ENUM ('active', 'expired');
        CREATE TYPE monitoring_status AS ENUM ('active', 'paused');
        CREATE TYPE scheduler_status AS ENUM ('idle', 'running', 'paused', 'error');
    """))
    
    # Create stock table
    conn.execute(text("""
        CREATE TABLE stock (
            stock_id SERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL UNIQUE,
            company_name VARCHAR(255) NOT NULL,
            status stock_status NOT NULL DEFAULT 'active',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        );
        
        CREATE INDEX idx_stock_ticker ON stock(ticker);
        CREATE INDEX idx_stock_status ON stock(status);
    """))
    
    # Create historical_premium_records table
    conn.execute(text("""
        CREATE TABLE historical_premium_records (
            record_id SERIAL,
            stock_id INTEGER NOT NULL REFERENCES stock(stock_id) ON DELETE CASCADE,
            collection_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            option_type option_type NOT NULL,
            strike_price NUMERIC(10, 2) NOT NULL,
            expiration_date DATE NOT NULL,
            days_to_expiry INTEGER NOT NULL,
            contract_status contract_status NOT NULL,
            premium NUMERIC(10, 2) NOT NULL,
            stock_price_at_collection NUMERIC(10, 2) NOT NULL,
            implied_volatility NUMERIC(6, 4),
            delta NUMERIC(6, 4),
            gamma NUMERIC(6, 4),
            theta NUMERIC(6, 4),
            vega NUMERIC(6, 4),
            rho NUMERIC(6, 4),
            volume INTEGER,
            open_interest INTEGER,
            data_source VARCHAR(50) DEFAULT 'yahoo_finance',
            scraper_run_id VARCHAR(50),
            PRIMARY KEY (record_id, collection_timestamp)
        );
        
        CREATE INDEX idx_collection_ts ON historical_premium_records(collection_timestamp DESC);
        CREATE INDEX idx_stock_option_strike ON historical_premium_records(stock_id, option_type, strike_price);
        CREATE INDEX idx_expiration ON historical_premium_records(expiration_date, contract_status);
        CREATE INDEX idx_stock_collection ON historical_premium_records(stock_id, collection_timestamp DESC);
    """))
    
    # Create watchlist table
    conn.execute(text("""
        CREATE TABLE watchlist (
            watchlist_id SERIAL PRIMARY KEY,
            stock_id INTEGER NOT NULL UNIQUE REFERENCES stock(stock_id) ON DELETE CASCADE,
            added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            monitoring_status monitoring_status NOT NULL DEFAULT 'active',
            notes TEXT
        );
        
        CREATE INDEX idx_watchlist_monitoring ON watchlist(monitoring_status);
    """))
    
    # Create scraper_schedule table (singleton)
    conn.execute(text("""
        CREATE TABLE scraper_schedule (
            schedule_id SERIAL PRIMARY KEY,
            polling_interval_minutes INTEGER NOT NULL DEFAULT 5,
            market_hours_start TIME NOT NULL DEFAULT '09:30:00',
            market_hours_end TIME NOT NULL DEFAULT '16:00:00',
            timezone VARCHAR(50) NOT NULL DEFAULT 'America/New_York',
            risk_free_rate NUMERIC(5, 4) NOT NULL DEFAULT 0.045,
            scheduler_status scheduler_status NOT NULL DEFAULT 'idle',
            last_run_timestamp TIMESTAMP WITH TIME ZONE,
            next_run_timestamp TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """))


def downgrade() -> None:
    conn = op.get_bind()
    
    # Drop tables in reverse order
    conn.execute(text("DROP TABLE IF EXISTS scraper_schedule CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS watchlist CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS historical_premium_records CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS stock CASCADE;"))
    
    # Drop enums
    conn.execute(text("DROP TYPE IF EXISTS scheduler_status;"))
    conn.execute(text("DROP TYPE IF EXISTS monitoring_status;"))
    conn.execute(text("DROP TYPE IF EXISTS contract_status;"))
    conn.execute(text("DROP TYPE IF EXISTS option_type;"))
    conn.execute(text("DROP TYPE IF EXISTS stock_status;"))
