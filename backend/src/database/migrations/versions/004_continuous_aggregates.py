"""
Alembic Migration: Create Continuous Aggregates for Daily Premium Summaries

Creates TimescaleDB continuous aggregate (materialized view) for pre-computed 
daily premium statistics. Improves query performance for historical analysis.

Revision ID: 004_continuous_aggregates
Revises: 003_seed_watchlist
Create Date: 2025-12-17
"""
from alembic import op
from sqlalchemy import text

# Revision identifiers
revision = '004_continuous_aggregates'
down_revision = '003_seed_watchlist'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create continuous aggregate for daily premium summaries.
    
    Per data-model.md: Pre-computes daily MIN/MAX/AVG premiums grouped by 
    ticker, option_type, strike_price, and expiration_date for faster queries.
    
    Automatically refreshes incrementally as new data arrives.
    """
    conn = op.get_bind()
    
    # Create continuous aggregate (materialized view with automatic refresh)
    conn.execute(text("""
        CREATE MATERIALIZED VIEW daily_premium_summary
        WITH (timescaledb.continuous) AS
        SELECT 
            time_bucket('1 day', collection_timestamp) AS day,
            stock_id,
            option_type,
            strike_price,
            expiration_date,
            MIN(premium) AS min_premium,
            MAX(premium) AS max_premium,
            AVG(premium) AS avg_premium,
            AVG(delta) AS avg_delta,
            AVG(gamma) AS avg_gamma,
            AVG(theta) AS avg_theta,
            AVG(vega) AS avg_vega,
            AVG(rho) AS avg_rho,
            AVG(implied_volatility) AS avg_implied_volatility,
            AVG(stock_price_at_collection) AS avg_stock_price,
            COUNT(*) AS data_points
        FROM historical_premium_records
        GROUP BY day, stock_id, option_type, strike_price, expiration_date
        WITH NO DATA;
    """))
    
    # Create indexes on the continuous aggregate for faster queries
    conn.execute(text("""
        CREATE INDEX idx_daily_summary_day 
        ON daily_premium_summary (day DESC);
    """))
    
    conn.execute(text("""
        CREATE INDEX idx_daily_summary_stock_strike 
        ON daily_premium_summary (stock_id, strike_price, expiration_date);
    """))
    
    conn.execute(text("""
        CREATE INDEX idx_daily_summary_option_type 
        ON daily_premium_summary (option_type, day DESC);
    """))
    
    # Add refresh policy to automatically update the aggregate
    # Refreshes every hour for data older than 1 hour
    conn.execute(text("""
        SELECT add_continuous_aggregate_policy('daily_premium_summary',
            start_offset => INTERVAL '7 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour');
    """))


def downgrade():
    """Remove continuous aggregate and refresh policy"""
    conn = op.get_bind()
    
    # Drop the continuous aggregate (automatically removes refresh policy)
    conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS daily_premium_summary;"))
