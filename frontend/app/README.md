# Global Soccer Manager — Match Viewer

React + TypeScript + Vite live match UI wired to the FastAPI backend (REST + WebSocket).

## Prerequisites

- Node.js 20+
- Backend running on port 8000 (`cd backend && uvicorn app.main:app --reload`)

## Run

```bash
cd frontend/app
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). API calls use the Vite proxy (`/api` → `http://127.0.0.1:8000`).

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm test` | Unit tests (Vitest) |

## Environment

Optional `.env`:

```
VITE_API_BASE=http://127.0.0.1:8000
VITE_WS_BASE=ws://127.0.0.1:8000
```

Defaults use `/api` proxy in development.