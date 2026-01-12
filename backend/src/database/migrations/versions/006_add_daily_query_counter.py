"""Add daily API query counter to scraper_schedule

Revision ID: 006_add_daily_query_counter
Revises: 91105e441b11
Create Date: 2026-01-08 15:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_daily_query_counter'
down_revision = '91105e441b11'
branch_labels = None
depends_on = None


def upgrade():
    """Add daily_api_queries and last_reset_date columns to scraper_schedule table"""
    
    # Add daily_api_queries column
    op.add_column(
        'scraper_schedule',
        sa.Column(
            'daily_api_queries',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Count of API queries made today (resets at 7:30 AM EST)'
        )
    )
    
    # Add last_reset_date column
    op.add_column(
        'scraper_schedule',
        sa.Column(
            'last_reset_date',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Last time the daily counter was reset'
        )
    )


def downgrade():
    """Remove daily_api_queries and last_reset_date columns"""
    
    op.drop_column('scraper_schedule', 'last_reset_date')
    op.drop_column('scraper_schedule', 'daily_api_queries')
