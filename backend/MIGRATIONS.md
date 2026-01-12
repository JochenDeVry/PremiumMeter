# Database Migrations Guide

This guide explains how to manage database migrations for the Options Premium Analyzer application.

## Table of Contents

- [Overview](#overview)
- [Migration Methods](#migration-methods)
- [CLI Method (Recommended)](#cli-method-recommended)
- [API Method](#api-method)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Overview

The application uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. Migrations are version-controlled files that describe changes to the database schema over time.

## Migration Methods

There are two ways to run migrations:

1. **CLI Method** (Recommended for production)
2. **API Method** (Useful for development/testing)

## CLI Method (Recommended)

### Prerequisites

```bash
# Ensure you're in the backend directory
cd backend

# Install dependencies if not already done
pip install -r requirements.txt
```

### Check Migration Status

```bash
alembic current
```

Shows the current database revision.

### View Pending Migrations

```bash
alembic history
```

Shows all available migrations with status indicators.

### Apply All Pending Migrations

```bash
alembic upgrade head
```

Applies all migrations up to the latest version.

### Apply Specific Migration

```bash
alembic upgrade <revision_id>
```

Example:
```bash
alembic upgrade 006_add_daily_query_counter
```

### Rollback One Migration

```bash
alembic downgrade -1
```

### Rollback to Specific Revision

```bash
alembic downgrade <revision_id>
```

### View SQL Without Executing

```bash
alembic upgrade head --sql
```

Useful for reviewing changes before applying.

## API Method

The application provides REST API endpoints for programmatic migration control.

⚠️ **Security Warning**: These endpoints modify database schema. In production, add authentication and restrict access appropriately.

### Check Migration Status

```bash
GET /api/migrations/status
```

**Example using curl:**
```bash
curl http://localhost:8000/api/migrations/status
```

**Response:**
```json
{
  "current_revision": "20251229_1445_91105e441b11",
  "available_revisions": [
    "001_create_core_tables",
    "002_enable_timescaledb_hypertable",
    "003_seed_watchlist",
    "004_continuous_aggregates",
    "005_phase2_user_role",
    "20251229_1445_91105e441b11_add_scraper_run_logs",
    "006_add_daily_query_counter"
  ],
  "pending_migrations": [
    "006_add_daily_query_counter"
  ],
  "is_up_to_date": false
}
```

### Apply Migrations

```bash
POST /api/migrations/upgrade?revision=head
```

**Example using curl:**
```bash
# Apply all pending migrations
curl -X POST http://localhost:8000/api/migrations/upgrade

# Apply up to specific revision
curl -X POST "http://localhost:8000/api/migrations/upgrade?revision=006_add_daily_query_counter"
```

**Response:**
```json
{
  "success": true,
  "message": "Database successfully upgraded to 006_add_daily_query_counter",
  "old_revision": "20251229_1445_91105e441b11",
  "new_revision": "006_add_daily_query_counter",
  "migrations_applied": [
    "006_add_daily_query_counter"
  ]
}
```

### Rollback Migration

```bash
POST /api/migrations/downgrade?revision=-1
```

**Example using curl:**
```bash
# Rollback one step
curl -X POST "http://localhost:8000/api/migrations/downgrade?revision=-1"

# Rollback to specific revision
curl -X POST "http://localhost:8000/api/migrations/downgrade?revision=005_phase2_user_role"
```

**Response:**
```json
{
  "success": true,
  "message": "Database successfully downgraded to 20251229_1445_91105e441b11",
  "old_revision": "006_add_daily_query_counter",
  "new_revision": "20251229_1445_91105e441b11",
  "migrations_applied": []
}
```

### Using PowerShell

```powershell
# Check status
Invoke-RestMethod -Uri "http://localhost:8000/api/migrations/status" -Method Get

# Apply migrations
Invoke-RestMethod -Uri "http://localhost:8000/api/migrations/upgrade" -Method Post

# Rollback one step
Invoke-RestMethod -Uri "http://localhost:8000/api/migrations/downgrade?revision=-1" -Method Post
```

## Common Tasks

### Initial Database Setup

```bash
# Method 1: CLI
cd backend
alembic upgrade head

# Method 2: API
curl -X POST http://localhost:8000/api/migrations/upgrade
```

### Adding Daily Query Counter (Latest Migration)

This migration adds tracking for daily API query counts with automatic reset at 7:30 AM EST.

```bash
# CLI Method
alembic upgrade 006_add_daily_query_counter

# API Method
curl -X POST "http://localhost:8000/api/migrations/upgrade?revision=006_add_daily_query_counter"
```

### Docker Environment

```bash
# Apply migrations inside running container
docker exec -it premiummeter_backend alembic upgrade head

# Or use API from host
curl -X POST http://localhost:8000/api/migrations/upgrade
```

### Verify Migration Success

```bash
# CLI
alembic current

# API
curl http://localhost:8000/api/migrations/status | jq '.is_up_to_date'
# Should return: true
```

## Troubleshooting

### Migration Already Applied

If you get an error that a migration is already applied, check the current status:

```bash
alembic current
```

The database tracks which migrations have been applied in the `alembic_version` table.

### Alembic Not Found

Ensure you're in the correct directory and dependencies are installed:

```bash
cd backend
pip install -r requirements.txt
```

### Database Connection Error

Check your database URL in `.env` file:

```
DATABASE_URL=postgresql://premiummeter:your_password@localhost:5432/premiummeter
```

For Docker:
```
DATABASE_URL=postgresql://premiummeter:your_password@db:5433/premiummeter
```

### API Endpoint Returns 500 Error

Common causes:
1. `alembic.ini` file not found - ensure it exists in `backend/` directory
2. Database connection issues - verify `DATABASE_URL` in settings
3. Permission issues - check database user has schema modification privileges

Check backend logs:
```bash
docker logs premiummeter_backend
```

### Checking Applied Migrations in Database

```sql
-- Connect to database and run:
SELECT * FROM alembic_version;
```

This shows the current revision stored in the database.

### Manual Cleanup (Use with Caution)

If migrations are stuck or corrupted:

```bash
# Stamp database to specific revision without running migrations
alembic stamp <revision_id>

# Reset to base (WARNING: This doesn't undo schema changes)
alembic stamp base
```

## Creating New Migrations

To create a new migration file:

```bash
cd backend
alembic revision -m "description of changes"
```

This creates a new file in `backend/src/database/migrations/versions/` with `upgrade()` and `downgrade()` functions to implement.

## Best Practices

1. **Always backup before migrating** production databases
2. **Test migrations** on a copy of production data first
3. **Use CLI method** for production deployments
4. **Review SQL** before applying: `alembic upgrade head --sql`
5. **Never manually edit** the `alembic_version` table unless absolutely necessary
6. **Keep migrations reversible** when possible (implement `downgrade()`)
7. **Version control** all migration files in git

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Alembic Integration](https://fastapi.tiangolo.com/tutorial/sql-databases/#alembic-note)
- [PostgreSQL Migration Best Practices](https://www.postgresql.org/docs/current/ddl-alter.html)
