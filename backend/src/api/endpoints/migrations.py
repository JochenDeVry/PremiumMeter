"""
Database Migrations API Endpoint

Provides endpoint to run Alembic database migrations programmatically.
USE WITH CAUTION: Only for development/testing or automated deployments.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
import os

from ...config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/migrations", tags=["migrations"])


class MigrationStatus(BaseModel):
    """Current migration status"""
    current_revision: Optional[str]
    available_revisions: List[str]
    pending_migrations: List[str]
    is_up_to_date: bool


class MigrationResult(BaseModel):
    """Result of migration operation"""
    success: bool
    message: str
    old_revision: Optional[str]
    new_revision: Optional[str]
    migrations_applied: List[str]


def get_alembic_config() -> Config:
    """Get Alembic configuration"""
    # Get the project root directory (where alembic.ini is located)
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
    
    if not os.path.exists(alembic_ini_path):
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")
    
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    
    return alembic_cfg


def get_current_revision() -> Optional[str]:
    """Get current database revision"""
    engine = create_engine(settings.database_url)
    
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()
    finally:
        engine.dispose()


def get_script_directory() -> ScriptDirectory:
    """Get Alembic script directory"""
    alembic_cfg = get_alembic_config()
    return ScriptDirectory.from_config(alembic_cfg)


@router.get("/status", response_model=MigrationStatus)
async def get_migration_status() -> MigrationStatus:
    """
    Get current migration status.
    Shows current revision, available revisions, and pending migrations.
    """
    try:
        current_rev = get_current_revision()
        script_dir = get_script_directory()
        
        # Get all available revisions
        all_revisions = [rev.revision for rev in script_dir.walk_revisions()]
        all_revisions.reverse()  # Oldest first
        
        # Determine pending migrations
        pending = []
        if current_rev:
            found_current = False
            for rev in all_revisions:
                if found_current:
                    pending.append(rev)
                elif rev == current_rev:
                    found_current = True
        else:
            # No current revision means all migrations are pending
            pending = all_revisions
        
        return MigrationStatus(
            current_revision=current_rev,
            available_revisions=all_revisions,
            pending_migrations=pending,
            is_up_to_date=len(pending) == 0
        )
    
    except Exception as e:
        logger.error(f"Error getting migration status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get migration status: {str(e)}"
        )


@router.post("/upgrade", response_model=MigrationResult)
async def upgrade_database(revision: str = "head") -> MigrationResult:
    """
    Run database migrations to upgrade to specified revision.
    
    Args:
        revision: Target revision (default: "head" for latest)
    
    Returns:
        Result of migration operation
    
    WARNING: This modifies the database schema. Use with caution.
    """
    try:
        # Get current revision before upgrade
        old_revision = get_current_revision()
        
        # Get pending migrations
        script_dir = get_script_directory()
        all_revisions = [rev.revision for rev in script_dir.walk_revisions()]
        all_revisions.reverse()
        
        pending = []
        if old_revision:
            found_current = False
            for rev in all_revisions:
                if found_current:
                    pending.append(rev)
                elif rev == old_revision:
                    found_current = True
        else:
            pending = all_revisions
        
        # Run migration
        alembic_cfg = get_alembic_config()
        command.upgrade(alembic_cfg, revision)
        
        # Get new revision after upgrade
        new_revision = get_current_revision()
        
        logger.info(f"Database upgraded from {old_revision} to {new_revision}")
        
        return MigrationResult(
            success=True,
            message=f"Database successfully upgraded to {new_revision}",
            old_revision=old_revision,
            new_revision=new_revision,
            migrations_applied=pending if revision == "head" else [revision]
        )
    
    except Exception as e:
        logger.error(f"Error upgrading database: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upgrade database: {str(e)}"
        )


@router.post("/downgrade", response_model=MigrationResult)
async def downgrade_database(revision: str) -> MigrationResult:
    """
    Downgrade database to specified revision.
    
    Args:
        revision: Target revision to downgrade to (e.g., "-1" for one step back)
    
    Returns:
        Result of migration operation
    
    WARNING: This can result in data loss. Use with extreme caution.
    """
    try:
        old_revision = get_current_revision()
        
        # Run downgrade
        alembic_cfg = get_alembic_config()
        command.downgrade(alembic_cfg, revision)
        
        new_revision = get_current_revision()
        
        logger.warning(f"Database downgraded from {old_revision} to {new_revision}")
        
        return MigrationResult(
            success=True,
            message=f"Database successfully downgraded to {new_revision}",
            old_revision=old_revision,
            new_revision=new_revision,
            migrations_applied=[]  # Downgrade doesn't "apply" migrations
        )
    
    except Exception as e:
        logger.error(f"Error downgrading database: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to downgrade database: {str(e)}"
        )
