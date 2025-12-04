#!/bin/sh
set -e

# Runtime configuration for the frontend
# This allows setting environment variables at container startup

# In Docker, nginx proxies /api to admin-api, so use relative URL
# For external access, API_URL env var can override this
cat > /usr/share/nginx/html/config.js << EOF
// Runtime configuration - generated at container startup
// In Docker: nginx proxies /api/* to admin-api:8000
window.ADMIN_CONFIG = {
  API_URL: "${EXTERNAL_API_URL:-/api}"
};
window.__RUNTIME_CONFIG__ = {
  API_URL: "${EXTERNAL_API_URL:-/api}",
  QDRANT_URL: "${QDRANT_URL:-http://qdrant:6333}",
  APP_VERSION: "${APP_VERSION:-1.0.0}",
  ENV: "${NODE_ENV:-production}"
};
EOF

echo "Runtime config generated:"
cat /usr/share/nginx/html/config.js

# Execute the main command
exec "$@"
