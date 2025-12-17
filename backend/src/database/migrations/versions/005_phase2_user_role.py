"""
Alembic Migration: Create Phase 2 User and Role Entities

Creates User and Role tables for future multi-user support (not activated in MVP).
Schema designed to support migration from single-user to multi-user model.

Revision ID: 005_phase2_user_role
Revises: 004_continuous_aggregates
Create Date: 2025-12-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '005_phase2_user_role'
down_revision = '004_continuous_aggregates'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create User and Role tables for Phase 2 multi-user support.
    
    Per data-model.md and spec.md:
    - Role table: Admin (full access) and Viewer (query/visualize only)
    - User table: Authentication credentials, role assignment
    - Not activated in MVP but schema prepared for future migration
    """
    # Create Role table
    op.create_table(
        'role',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('name')
    )
    
    # Create index on role name
    op.create_index('idx_role_name', 'role', ['name'])
    
    # Create User table
    op.create_table(
        'user',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('account_status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['role.role_id'], name='fk_user_role'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # Create indexes on user table
    op.create_index('idx_user_username', 'user', ['username'])
    op.create_index('idx_user_email', 'user', ['email'])
    op.create_index('idx_user_role', 'user', ['role_id'])
    op.create_index('idx_user_status', 'user', ['account_status'])
    
    # Seed default roles
    op.execute("""
        INSERT INTO role (name, permissions) VALUES
        (
            'Admin',
            '["query_data", "view_charts", "manage_watchlist", "configure_scraper", "manage_users"]'::jsonb
        ),
        (
            'Viewer',
            '["query_data", "view_charts"]'::jsonb
        )
    """)


def downgrade():
    """Remove Phase 2 user and role tables"""
    # Drop tables in reverse order (user first due to foreign key)
    op.drop_table('user')
    op.drop_table('role')
