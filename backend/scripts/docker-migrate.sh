#!/bin/bash
# docker-migrate.sh — Safe migration wrapper for Docker containers.
# Detects stale migration state and gives clear recovery instructions
# instead of a cryptic Python traceback.

set -e

echo "FilaOps: Running database migrations..."

# First, check if alembic can find the current DB revision.
# If the DB was created by an older/different edition, the stamped
# revision won't exist in our migration files.
CURRENT_OUTPUT=$(alembic current 2>&1) || true

if echo "$CURRENT_OUTPUT" | grep -q "Can't locate revision"; then
    echo ""
    echo "================================================================"
    echo "  DATABASE MIGRATION MISMATCH DETECTED"
    echo "================================================================"
    echo ""
    echo "  Your database was created by a different version of FilaOps"
    echo "  and contains migration history that no longer exists."
    echo ""
    echo "  To fix this, remove the database volume and start fresh:"
    echo ""
    echo "    docker compose down"
    echo "    docker volume rm filaops_pgdata"
    echo "    docker compose up --build -d"
    echo ""
    echo "  This will create a clean database with all current migrations."
    echo "================================================================"
    echo ""
    exit 1
fi

# Normal migration — apply any pending migrations
alembic upgrade head

echo "FilaOps: Migrations complete."
