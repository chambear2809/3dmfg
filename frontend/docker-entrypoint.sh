#!/bin/sh
# Write runtime config for the frontend.
# This runs at container startup so the API URL can be set via environment
# variables without rebuilding the image.
cat > /usr/share/nginx/html/config.js << EOF
window.__FILAOPS_CONFIG__ = {
  API_URL: "${VITE_API_URL:-}"
};
EOF
exec "$@"
