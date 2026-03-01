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

# Plugin migrations — run if a plugin with its own Alembic config is installed.
# Each plugin uses a separate version table (e.g. alembic_version_pro) so
# plugin and Core migration chains never interfere.
if python -c "import filaops_pro" 2>/dev/null; then
    PRO_INI=$(python -c "import filaops_pro, os; print(os.path.join(os.path.dirname(filaops_pro.__file__), 'alembic.ini'))")
    if [ -f "$PRO_INI" ]; then
        echo "FilaOps: Running PRO plugin migrations..."
        alembic -c "$PRO_INI" upgrade head
        echo "FilaOps: PRO migrations complete."
    fi
fi

echo "FilaOps: Migrations complete."
