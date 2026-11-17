# Frontend

**Stack:** React 18, TypeScript, Vite 4 — live match viewer in `frontend/app/`.

## Run

```bash
# Terminal 1 — backend
cd backend && .venv\Scripts\uvicorn app.main:app --reload

# Terminal 2 — viewer
cd frontend/app && npm install && npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` (and WebSocket) to `http://127.0.0.1:8000`.

## Features

- SVG top-down pitch driven by engine `payload.pitch` (22 players + ball)
- Scoreboard, clock, commentary feed, live statistics
- Manager controls: controlled stepping, pause/resume, tactics, formation, substitutions
- Optional auto mode (background sim + WebSocket), same UI

Match data always comes from the API — no hardcoded scores or events.