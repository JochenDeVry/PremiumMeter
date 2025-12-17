"""
Alembic Migration: Seed Initial Watchlist

Creates initial watchlist with 54 US stocks as specified in spec.md.

Revision ID: 003_seed_watchlist
Revises: 002_timescaledb
Create Date: 2025-12-17
"""
from alembic import op
from sqlalchemy import text
from datetime import datetime

# Revision identifiers
revision = '003_seed_watchlist'
down_revision = '002_timescaledb'
branch_labels = None
depends_on = None


def upgrade():
    """
    Seed initial 54-stock watchlist from spec.md.
    
    Stocks: ADBE, AMD, BABA, GOOGL, GOOG, AMZN, AAL, AAPL, APLD, ACHR, TEAM, BMNR, 
    BA, AVGO, CAVA, CMG, CEG, CRWV, ELV, RACE, GME, HIMS, INTC, KVUE, LULU, META, 
    MSFT, MDB, NBIS, NFLX, NKE, NIO, NVDA, OKLO, OPEN, ORCL, OSCR, PLTR, PYPL, PLUG, 
    RDDT, RGTI, HOOD, SRPT, SHOP, SNAP, SOFI, SOUN, SMMT, TGT, TSLA, VST, W, WFBR
    """
    conn = op.get_bind()
    
    # Initial stock list with company names
    stocks = [
        ('ADBE', 'Adobe Inc.'),
        ('AMD', 'Advanced Micro Devices Inc.'),
        ('BABA', 'Alibaba Group Holding Ltd.'),
        ('GOOGL', 'Alphabet Inc. Class A'),
        ('GOOG', 'Alphabet Inc. Class C'),
        ('AMZN', 'Amazon.com Inc.'),
        ('AAL', 'American Airlines Group Inc.'),
        ('AAPL', 'Apple Inc.'),
        ('APLD', 'Applied Digital Corporation'),
        ('ACHR', 'Archer Aviation Inc.'),
        ('TEAM', 'Atlassian Corporation'),
        ('BMNR', 'Brookfield Infrastructure Partners'),
        ('BA', 'The Boeing Company'),
        ('AVGO', 'Broadcom Inc.'),
        ('CAVA', 'CAVA Group Inc.'),
        ('CMG', 'Chipotle Mexican Grill Inc.'),
        ('CEG', 'Constellation Energy Corporation'),
        ('CRWV', 'Crown Electrokinetics Corp.'),
        ('ELV', 'Elevance Health Inc.'),
        ('RACE', 'Ferrari N.V.'),
        ('GME', 'GameStop Corp.'),
        ('HIMS', 'Hims & Hers Health Inc.'),
        ('INTC', 'Intel Corporation'),
        ('KVUE', 'Kenvue Inc.'),
        ('LULU', 'Lululemon Athletica Inc.'),
        ('META', 'Meta Platforms Inc.'),
        ('MSFT', 'Microsoft Corporation'),
        ('MDB', 'MongoDB Inc.'),
        ('NBIS', 'Nebius Group N.V.'),
        ('NFLX', 'Netflix Inc.'),
        ('NKE', 'NIKE Inc.'),
        ('NIO', 'NIO Inc.'),
        ('NVDA', 'NVIDIA Corporation'),
        ('OKLO', 'Oklo Inc.'),
        ('OPEN', 'Opendoor Technologies Inc.'),
        ('ORCL', 'Oracle Corporation'),
        ('OSCR', 'Oscar Health Inc.'),
        ('PLTR', 'Palantir Technologies Inc.'),
        ('PYPL', 'PayPal Holdings Inc.'),
        ('PLUG', 'Plug Power Inc.'),
        ('RDDT', 'Reddit Inc.'),
        ('RGTI', 'Rigetti Computing Inc.'),
        ('HOOD', 'Robinhood Markets Inc.'),
        ('SRPT', 'Sarepta Therapeutics Inc.'),
        ('SHOP', 'Shopify Inc.'),
        ('SNAP', 'Snap Inc.'),
        ('SOFI', 'SoFi Technologies Inc.'),
        ('SOUN', 'SoundHound AI Inc.'),
        ('SMMT', 'Summit Therapeutics Inc.'),
        ('TGT', 'Target Corporation'),
        ('TSLA', 'Tesla Inc.'),
        ('VST', 'Vistra Corp.'),
        ('W', 'Wayfair Inc.'),
        ('WFBR', 'Wayfer Inc.')
    ]
    
    # Insert stocks
    for ticker, company_name in stocks:
        conn.execute(
            text("""
                INSERT INTO stock (ticker, company_name, status, created_at, updated_at)
                VALUES (:ticker, :company_name, 'active', :now, :now)
                ON CONFLICT (ticker) DO NOTHING
            """),
            {
                'ticker': ticker,
                'company_name': company_name,
                'now': datetime.now()
            }
        )
    
    # Add all stocks to watchlist
    conn.execute(
        text("""
            INSERT INTO watchlist (stock_id, monitoring_status, added_at)
            SELECT stock_id, 'active', :now
            FROM stock
            WHERE ticker IN :tickers
            ON CONFLICT (stock_id) DO NOTHING
        """),
        {
            'now': datetime.now(),
            'tickers': tuple([ticker for ticker, _ in stocks])
        }
    )
    
    # Create initial scraper schedule configuration
    conn.execute(
        text("""
            INSERT INTO scraper_schedule (
                polling_interval_minutes,
                market_hours_start,
                market_hours_end,
                timezone,
                risk_free_rate,
                scheduler_status,
                created_at,
                updated_at
            )
            VALUES (
                5,                     -- 5 minute polling interval
                '09:30:00',            -- Market open
                '16:00:00',            -- Market close
                'America/New_York',    -- Eastern Time
                0.045,                 -- 4.5% risk-free rate
                'idle',                -- Initial status
                :now,
                :now
            )
        """),
        {'now': datetime.now()}
    )


def downgrade():
    """Remove seeded data"""
    conn = op.get_bind()
    
    # Delete scraper schedule
    conn.execute(text("DELETE FROM scraper_schedule"))
    
    # Delete watchlist entries
    conn.execute(text("DELETE FROM watchlist"))
    
    # Delete stocks
    conn.execute(text("DELETE FROM stock"))
