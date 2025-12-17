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
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_create_core'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE stock_status AS ENUM ('active', 'delisted', 'inactive')")
    op.execute("CREATE TYPE option_type AS ENUM ('call', 'put')")
    op.execute("CREATE TYPE contract_status AS ENUM ('active', 'expired')")
    op.execute("CREATE TYPE monitoring_status AS ENUM ('active', 'paused')")
    op.execute("CREATE TYPE scheduler_status AS ENUM ('idle', 'running', 'paused', 'error')")

    # Create stocks table
    op.create_table(
        'stocks',
        sa.Column('stock_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'delisted', 'inactive', name='stock_status'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('stock_id'),
        sa.UniqueConstraint('ticker')
    )
    op.create_index('idx_stocks_ticker', 'stocks', ['ticker'])
    op.create_index('idx_stocks_status', 'stocks', ['status'])

    # Create historical_premium_records table
    op.create_table(
        'historical_premium_records',
        sa.Column('record_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('option_type', postgresql.ENUM('call', 'put', name='option_type'), nullable=False),
        sa.Column('strike_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=False),
        sa.Column('premium', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('stock_price_at_collection', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('delta', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('gamma', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('theta', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('vega', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('contract_status', postgresql.ENUM('active', 'expired', name='contract_status'), nullable=False),
        sa.Column('days_to_expiry', sa.Integer(), nullable=False),
        sa.Column('collection_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.stock_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('record_id')
    )
    # Composite index for main query pattern
    op.create_index('idx_premium_query_main', 'historical_premium_records', ['stock_id', 'option_type', 'strike_price', 'days_to_expiry', 'collection_timestamp'])
    op.create_index('idx_premium_collection_time', 'historical_premium_records', ['collection_timestamp'])
    op.create_index('idx_premium_stock_time', 'historical_premium_records', ['stock_id', 'collection_timestamp'])
    op.create_index('idx_premium_strike_range', 'historical_premium_records', ['stock_id', 'option_type', 'strike_price'])
    op.create_index('idx_premium_expiration', 'historical_premium_records', ['expiration_date', 'contract_status'])

    # Create watchlist table
    op.create_table(
        'watchlist',
        sa.Column('watchlist_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'paused', name='monitoring_status'), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.stock_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('watchlist_id'),
        sa.UniqueConstraint('stock_id', name='uq_watchlist_stock')
    )
    op.create_index('idx_watchlist_stock', 'watchlist', ['stock_id'])
    op.create_index('idx_watchlist_status', 'watchlist', ['status'])

    # Create scraper_schedule table
    op.create_table(
        'scraper_schedule',
        sa.Column('config_id', sa.Integer(), nullable=False, default=1),
        sa.Column('polling_interval_minutes', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('market_hours_start', sa.Time(), nullable=False, server_default='09:30:00'),
        sa.Column('market_hours_end', sa.Time(), nullable=False, server_default='16:00:00'),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='America/New_York'),
        sa.Column('exclude_weekends', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('exclude_holidays', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status', postgresql.ENUM('idle', 'running', 'paused', 'error', name='scheduler_status'), nullable=False, server_default='idle'),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_message', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('config_id'),
        sa.CheckConstraint('config_id = 1', name='single_config_row')
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table('scraper_schedule')
    op.drop_table('watchlist')
    op.drop_table('historical_premium_records')
    op.drop_table('stocks')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS scheduler_status')
    op.execute('DROP TYPE IF EXISTS monitoring_status')
    op.execute('DROP TYPE IF EXISTS contract_status')
    op.execute('DROP TYPE IF EXISTS option_type')
    op.execute('DROP TYPE IF EXISTS stock_status')
