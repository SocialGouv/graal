# Database Setup Guide

This guide walks you through setting up the PostgreSQL database for local GRAAL development.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Step-by-Step Setup](#step-by-step-setup)
- [Database Management](#database-management)
- [Troubleshooting](#troubleshooting)
- [Development Workflow](#development-workflow)

---

## Quick Start

**TL;DR:** Get the database running in 5 minutes:

```bash
# 1. Install dependencies
make install

# 2. Set up environment
cp .env.example .env
# Edit .env if needed (defaults work for local dev)

# 3. Start PostgreSQL + pgAdmin
docker-compose up -d

# 4. Run migrations
poetry run alembic upgrade head

# 5. Seed test data (optional)
poetry run python scripts/init_db.py

# 6. Access pgAdmin at http://localhost:5050
#    User: graal_user
#    Password: graal_local_pass
```

---

## Prerequisites

### Required Software

- **Docker** and **Docker Compose** (for PostgreSQL and pgAdmin)
- **Python 3.11+** (project requirement)
- **Poetry** (dependency management)

### Installation

```bash
# Install Docker (if not already installed)
# macOS: Download from https://www.docker.com/products/docker-desktop
# Linux: sudo apt-get install docker.io docker-compose

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Verify installations
docker --version
docker-compose --version
poetry --version
```

---

## Step-by-Step Setup

### 1. Install Python Dependencies

Install the database-related Python packages:

```bash
# Activate poetry shell
poetry shell

# Install all dependencies (includes database packages)
poetry install

# Verify SQLAlchemy installation
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

This installs:
- `sqlalchemy[asyncio]>=2.0.0` - Async ORM
- `asyncpg>=0.29.0` - PostgreSQL async driver
- `alembic>=1.13.0` - Database migrations
- `psycopg2-binary>=2.9.9` - PostgreSQL adapter for Alembic
- `authlib>=1.3.0` - OAuth support for future ProConnect integration

### 2. Configure Environment Variables

Create your local environment file:

```bash
# Copy the example file
cp .env.example .env

# Edit if needed (optional for local development)
nano .env
```

**Default local settings** (already in `.env.example`):
```bash
DATABASE_URL="postgresql://graal_user:graal_local_pass@localhost:5432/graal_dev?sslmode=prefer"
```

**For remote environments**, use the split format:
```bash
DB_HOST="pg-rw"
DB_PORT="5432"
DB_NAME="preprod"
DB_USER="preprod"
DB_PASSWORD="<secure_password>"
DB_SSL_MODE="require"
```

### 3. Start Database Services

Start PostgreSQL and pgAdmin using Docker Compose:

```bash
# Start services in background
docker-compose up -d

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f postgres
```

**Services started:**
- **PostgreSQL 16** on `localhost:5432`
- **pgAdmin 4** on `http://localhost:5050`

### 4. Run Database Migrations

Apply the database schema using Alembic:

```bash
# Ensure you're in poetry shell
poetry shell

# Run migrations
alembic upgrade head

# Verify migration was applied
alembic current
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema, Initial database schema
```

### 5. Seed Test Data (Optional)

Populate the database with test users and sample data:

```bash
# Run seed script
poetry run python scripts/init_db.py
```

**What gets created:**
- **2 Users:**
  - `admin@graal.com` (admin, ProConnect sub: `admin-test-sub-001`)
  - `user@graal.local` (regular user, ProConnect sub: `user-test-sub-001`)
- **3 Configurations:** Sample processing configurations
- **4 Processing Jobs:** Examples in various states (completed, running, failed, queued)
- **3 Similarity DB Manifests:** Sample database references

### 6. Verify Setup

Access pgAdmin to verify the database:

1. Open http://localhost:5050 in your browser
2. Login with:
   - Email: `admin@graal.com`
   - Password: `admin`
3. The server connection should be pre-configured
4. Browse to: **Servers → GRAAL Local Database → Databases → graal_dev → Schemas → public → Tables**

You should see 4 tables:
- `users`
- `user_configurations`
- `processing_jobs`
- `similarity_db_manifests`

---

## Database Management

### Alembic Migrations

**Create a new migration:**
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Review the generated migration file
# Edit alembic/versions/*.py if needed

# Apply the migration
alembic upgrade head
```

**Rollback a migration:**
```bash
# Downgrade by 1 revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>

# Downgrade all the way
alembic downgrade base
```

**Check migration status:**
```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic show head
```

### Docker Compose Commands

**Start/Stop services:**
```bash
# Start services
docker-compose up -d

# Stop services (preserves data)
docker-compose stop

# Stop and remove containers (preserves data volumes)
docker-compose down

# Stop and remove everything INCLUDING data
docker-compose down -v
```

**View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f pgadmin
```

**Restart services:**
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart postgres
```

### Database Backup & Restore

**Backup database:**
```bash
# Using Docker
docker-compose exec postgres pg_dump -U graal_user graal_dev > backup.sql

# Or using pg_dump directly
pg_dump -h localhost -p 5432 -U graal_user graal_dev > backup.sql
```

**Restore database:**
```bash
# Using Docker
docker-compose exec -T postgres psql -U graal_user graal_dev < backup.sql

# Or using psql directly
psql -h localhost -p 5432 -U graal_user graal_dev < backup.sql
```

**Reset database (start fresh):**
```bash
# Stop and remove all data
docker-compose down -v

# Start services again
docker-compose up -d

# Run migrations
alembic upgrade head

# Seed data
poetry run python scripts/init_db.py
```

---

## Troubleshooting

### Connection Issues

**Problem:** `could not connect to server: Connection refused`

**Solutions:**
```bash
# Check if PostgreSQL is running
docker-compose ps

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Verify port 5432 is not in use
lsof -i :5432
```

### Migration Errors

**Problem:** `Target database is not up to date`

**Solution:**
```bash
# Check current revision
alembic current

# Show what needs to be applied
alembic history

# Upgrade to latest
alembic upgrade head
```

**Problem:** `Can't locate revision identified by 'xxx'`

**Solution:**
```bash
# Stamp database with current revision
alembic stamp head

# Or start fresh
alembic downgrade base
alembic upgrade head
```

### pgAdmin Issues

**Problem:** Can't access pgAdmin at http://localhost:5050

**Solutions:**
```bash
# Check if pgAdmin is running
docker-compose ps

# Check pgAdmin logs
docker-compose logs pgadmin

# Restart pgAdmin
docker-compose restart pgadmin

# Verify port 5050 is available
lsof -i :5050
```

**Problem:** Server connection not showing in pgAdmin

**Solution:**
1. The connection is auto-configured via `docker/pgadmin-servers.json`
2. If missing, add manually:
   - Right-click **Servers** → **Register** → **Server**
   - **General tab:** Name: "GRAAL Local Database"
   - **Connection tab:**
     - Host: `postgres`
     - Port: `5432`
     - Database: `graal_dev`
     - Username: `graal_user`
     - Password: `graal_local_pass`

### Permission Errors

**Problem:** `permission denied for schema public`

**Solution:**
```bash
# Connect to database
docker-compose exec postgres psql -U graal_user graal_dev

# Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA public TO graal_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO graal_user;
\q
```

### Port Conflicts

**Problem:** `port is already allocated`

**Solutions:**

**Option 1:** Stop the conflicting service
```bash
# Find what's using the port
lsof -i :5432  # or :5050 for pgAdmin

# Stop it or change docker-compose.yml ports
```

**Option 2:** Change ports in `docker-compose.yml`
```yaml
services:
  postgres:
    ports:
      - "5433:5432"  # Use 5433 on host instead
  pgadmin:
    ports:
      - "5051:80"    # Use 5051 on host instead
```

Then update `DATABASE_URL` in `.env`:
```bash
DATABASE_URL="postgresql://graal_user:graal_local_pass@localhost:5433/graal_dev?sslmode=prefer"
```

---

## Development Workflow

### Daily Development

```bash
# 1. Ensure database is running
docker-compose up -d

# 2. Activate poetry shell
poetry shell

# 3. Start development server
uvicorn graal.api.main:app --reload

# 4. Make changes to models, run tests, etc.

# 5. When done, optionally stop database
docker-compose stop
```

### Making Schema Changes

```bash
# 1. Modify models in graal/database/models.py

# 2. Create migration
alembic revision --autogenerate -m "add new column to users"

# 3. Review generated migration in alembic/versions/

# 4. Apply migration
alembic upgrade head

# 5. Update seed data if needed in scripts/init_db.py
```

### Testing with Fresh Data

```bash
# Reset database
docker-compose down -v
docker-compose up -d

# Apply migrations
alembic upgrade head

# Seed test data
poetry run python scripts/init_db.py

# Run tests
pytest tests/
```

### Working with Remote Databases

**For development/staging environments:**

```bash
# Set environment variables for remote DB
export DB_HOST="pg-rw"
export DB_PORT="5432"
export DB_NAME="preprod"
export DB_USER="preprod"
export DB_PASSWORD="<password>"
export DB_SSL_MODE="require"

# Run migrations
alembic upgrade head

# DON'T seed data on production/staging
```

---

## Next Steps

After completing Phase 1 setup:

- **Phase 2:** Integrate ProConnect authentication
  - Implement OAuth 2.0 / OpenID Connect flow
  - Replace `HardcodedAuthorizationProvider` with `DatabaseAuthorizationProvider`
  - Add session management

- **Phase 3:** Migrate job tracking to database
  - Replace `InMemoryJobRegistry` with `DatabaseJobRegistry`
  - Add job history and search features

- **Phase 4:** Implement full feature set
  - User configuration management
  - Similarity database manifest tracking
  - Usage analytics

---

## Additional Resources

- [Architecture Plan](./database_architecture_plan.md) - Complete database design and roadmap
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [asyncpg Docs](https://magicstack.github.io/asyncpg/)
- [ProConnect Docs](https://partenaires.proconnect.gouv.fr/docs/fournisseur-service)

---

## Support

If you encounter issues not covered in this guide:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs: `docker-compose logs`
3. Verify environment variables: `cat .env`
4. Ask the team on Slack/Teams
