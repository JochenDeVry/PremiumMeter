"""002_enable_timescaledb_hypertable

Revision ID: 002_timescaledb
Revises: 001_create_core
Create Date: 2025-12-16 21:05:00.000000

Migration: Convert historical_premium_records to TimescaleDB hypertable
- Enable TimescaleDB extension
- Convert table to hypertable partitioned by collection_timestamp
- Set chunk interval to 1 day (optimized for intra-day 5-minute polling)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_timescaledb'
down_revision: Union[str, None] = '001_create_core'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable TimescaleDB extension (requires superuser or appropriate permissions)
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    # Convert historical_premium_records to hypertable
    # Partitioned by collection_timestamp with 1-day chunks
    # Optimized for intra-day polling (5-min interval = 288 data points per stock per day)
    op.execute("""
        SELECT create_hypertable(
            'historical_premium_records',
            'collection_timestamp',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        )
    """)

    # Enable compression on hypertable for data older than 7 days
    # Compress by stock_id and option_type for better query performance
    op.execute("""
        ALTER TABLE historical_premium_records SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'stock_id,option_type',
            timescaledb.compress_orderby = 'collection_timestamp DESC'
        )
    """)

    # Add compression policy: compress chunks older than 7 days
    op.execute("""
        SELECT add_compression_policy('historical_premium_records', INTERVAL '7 days')
    """)

    # Add retention policy: drop chunks older than 1 year (optional)
    # Commented out by default - enable if data retention needs to be limited
    # op.execute("""
    #     SELECT add_retention_policy('historical_premium_records', INTERVAL '365 days')
    # """)


def downgrade() -> None:
    # Remove compression policy
    op.execute("""
        SELECT remove_compression_policy('historical_premium_records', if_exists => true)
    """)

    # Remove retention policy (if enabled)
    # op.execute("""
    #     SELECT remove_retention_policy('historical_premium_records', if_exists => true)
    # """)

    # Disable compression
    op.execute("""
        ALTER TABLE historical_premium_records SET (
            timescaledb.compress = false
        )
    """)

    # Cannot directly revert hypertable to regular table in TimescaleDB
    # Would need to create new table and migrate data
    # For development, recommend dropping and recreating database
    # Production downgrade would require custom migration script

    # Note: Keeping hypertable structure on downgrade to prevent data loss
    # To fully remove TimescaleDB:
    # 1. Create backup of data
    # 2. Drop hypertable
    # 3. Recreate as regular table
    # 4. Restore data
    # 5. DROP EXTENSION timescaledb CASCADE (only if no other hypertables exist)
