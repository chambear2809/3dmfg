#!/bin/bash
# docker-entrypoint.sh — Container startup script.
# Downloads PRO plugin if license key is set, then delegates to
# the Python entrypoint which reliably sets env vars before exec.

set -e

# ─── PRO Plugin Auto-Download ───
if [ -n "$FILAOPS_LICENSE_KEY" ]; then
    if ! python -c "import filaops_pro" 2>/dev/null; then
        echo "FilaOps: License key detected. Downloading PRO plugin..."
        LICENSE_URL="${LICENSE_SERVER_URL:-https://license.blb3dprinting.com}"
        WHEEL_PATH="/tmp/filaops_pro.whl"

        if curl -sf -H "X-License-Key: $FILAOPS_LICENSE_KEY" \
            "$LICENSE_URL/api/v1/download/filaops-pro" \
            -o "$WHEEL_PATH"; then
            pip install --no-cache-dir -q "$WHEEL_PATH"
            rm -f "$WHEEL_PATH"
            echo "FilaOps: PRO plugin installed."
        else
            echo "FilaOps: Could not download PRO plugin. Starting in Community mode."
        fi
    fi
fi

# ─── Run Command ───
# Delegate to Python for reliable env var passing via os.execvp
if [ $# -gt 0 ]; then
    exec python /app/scripts/entrypoint.py "$@"
else
    exec python /app/scripts/entrypoint.py
fi
