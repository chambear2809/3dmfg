# FilaOps Frontend

React-based admin dashboard for FilaOps ERP.

## Tech Stack

- **React 19** with Vite
- **Node.js runtime service** for production static serving and same-origin proxying
- **Tailwind CSS** with custom neo-industrial dark theme
- **React Router** for navigation
- **Recharts** for data visualization

## Quick Start

```bash
npm install
npm run dev
```

Open <http://localhost:5173>

## Project Structure

```text
src/
├── components/     # Reusable UI components
├── hooks/          # Custom React hooks
├── lib/            # Utilities and API client
├── pages/          # Route components
│   └── admin/      # Admin dashboard pages
└── services/       # API service functions
```

## Environment Variables

Create `.env.local`:

```ini
VITE_API_URL=http://localhost:8000
```

## Building

```bash
npm run build
```

## Production Runtime

The production image serves the built SPA through
[`server.mjs`](/Users/alecchamberlain/Documents/GitHub/3d-mfg/frontend/server.mjs),
a small Node service that:

- serves the compiled Vite assets
- proxies `/api`, `/static`, and `/portal` to the backend
- proxies `/otel/v1/traces` to the cluster collector for same-origin browser export

This keeps the frontend visible as an auto-instrumented service in Kubernetes
while preserving browser RUM.
