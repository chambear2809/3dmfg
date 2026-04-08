#!/bin/sh
# Write runtime config for the frontend.
# This runs at container startup so the API URL can be set via environment
# variables without rebuilding the image.
set -eu

DIST_DIR="${FRONTEND_DIST_DIR:-/app/dist}"
mkdir -p "$DIST_DIR"

cat > "${DIST_DIR}/config.js" << EOF
window.__FILAOPS_CONFIG__ = {
  API_URL: "${VITE_API_URL:-}",
  SPLUNK_RUM_ENABLED: "${SPLUNK_RUM_ENABLED:-false}",
  SPLUNK_RUM_REALM: "${SPLUNK_RUM_REALM:-}",
  SPLUNK_RUM_ACCESS_TOKEN: "${SPLUNK_RUM_ACCESS_TOKEN:-}",
  SPLUNK_RUM_APP_NAME: "${SPLUNK_RUM_APP_NAME:-filaops-frontend}",
  SPLUNK_RUM_DEBUG: "${SPLUNK_RUM_DEBUG:-false}",
  SPLUNK_RUM_EXPORTER: "${SPLUNK_RUM_EXPORTER:-direct}",
  SPLUNK_RUM_BEACON_ENDPOINT: "${SPLUNK_RUM_BEACON_ENDPOINT:-}",
  SPLUNK_RUM_SESSION_SAMPLE_RATIO: "${SPLUNK_RUM_SESSION_SAMPLE_RATIO:-1}",
  SPLUNK_RUM_USER_TRACKING_MODE: "${SPLUNK_RUM_USER_TRACKING_MODE:-noTracking}",
  SPLUNK_RUM_SESSION_REPLAY_ENABLED: "${SPLUNK_RUM_SESSION_REPLAY_ENABLED:-false}",
  SPLUNK_RUM_MASK_ALL_TEXT: "${SPLUNK_RUM_MASK_ALL_TEXT:-false}",
  SPLUNK_RUM_MASK_ALL_INPUTS: "${SPLUNK_RUM_MASK_ALL_INPUTS:-true}",
  APP_ENV: "${APP_ENV:-production}",
  APP_VERSION: "${APP_VERSION:-unknown}"
};
EOF
exec "$@"
