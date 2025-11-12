# Admin Panel Documentation

Welcome to the Claude Self-Reflect Admin Panel documentation.

## Available Documentation

- **[ADMIN_PANEL_README.md](./ADMIN_PANEL_README.md)** - Complete overview (Portuguese)
- **[ADMIN_PANEL_SUMMARY.md](./ADMIN_PANEL_SUMMARY.md)** - Feature summary
- **[QUICK_START_ADMIN.md](./QUICK_START_ADMIN.md)** - Quick start guide
- **[TEST_ADMIN_PANEL.md](./TEST_ADMIN_PANEL.md)** - Testing guide

## Quick Start

```bash
# Start admin panel + API
./start-admin.sh

# Access
# Panel: http://localhost:3000
# API: http://localhost:8000

# Stop
./stop-admin.sh
```

## Features

- **Dashboard** - System metrics and status
- **Projects** - Project management
- **Imports** - Import monitoring
- **Collections** - Qdrant collection admin
- **Batch Jobs** - v7.0 AI narrative jobs
- **Docker** - Container management
- **Settings** - Configuration
- **Logs** - Log viewer

## Technology Stack

### Frontend (admin-panel/)
- React + TypeScript
- Vite + Tailwind CSS
- shadcn/ui components

### Backend (admin-api/)
- FastAPI + Uvicorn
- Async Python
- Qdrant integration

## Notes

⚠️ **Security**: Currently no authentication (localhost only)
⚠️ **Distribution**: Not included in npm package (separate deployment)

For main project documentation, see root `README.md`.
