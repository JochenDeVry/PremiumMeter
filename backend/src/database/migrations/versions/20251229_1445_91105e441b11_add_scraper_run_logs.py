"""
Mako template for generating migration files.
add_scraper_run_logs

Revision ID: 91105e441b11
Revises: 005_phase2_user_role
Create Date: 2025-12-29 14:45:45.097136+00:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '91105e441b11'
down_revision = '005_phase2_user_role'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create scraper_runs table
    op.create_table(
        'scraper_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('running', 'completed', 'failed', name='runstatus'), nullable=False),
        sa.Column('total_stocks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_stocks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_stocks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_contracts', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scraper_runs_id'), 'scraper_runs', ['id'], unique=False)
    
    # Create scraper_stock_logs table
    op.create_table(
        'scraper_stock_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('status', sa.Enum('success', 'failed', name='stockscrapestatus'), nullable=False),
        sa.Column('source_used', sa.String(length=50), nullable=True),
        sa.Column('contracts_scraped', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['scraper_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scraper_stock_logs_id'), 'scraper_stock_logs', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_scraper_stock_logs_id'), table_name='scraper_stock_logs')
    op.drop_table('scraper_stock_logs')
    op.drop_index(op.f('ix_scraper_runs_id'), table_name='scraper_runs')
    op.drop_table('scraper_runs')
    op.execute('DROP TYPE runstatus')
    op.execute('DROP TYPE stockscrapestatus')
