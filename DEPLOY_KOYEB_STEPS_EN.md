# Deploy YourMove on Koyeb (Production-Aligned Guide)

This guide is updated for the current YourMove codebase:
- FastAPI app entrypoint: `main.py`
- Startup DB init via SQLAlchemy metadata create
- Static pages served by FastAPI
- Real-time WebSockets for UE5 + dashboard
- Optional Gemini-based final report + local fallback

## 1) Prerequisites

- Your code is pushed to GitHub.
- `Dockerfile` is at repository root.
- App listens on `0.0.0.0` (already true in Dockerfile command).
- You have a PostgreSQL instance (Koyeb managed Postgres recommended).
- You have rotated all leaked/old secrets before deployment.

## 2) Required Environment Variables (Koyeb)

Set these in Koyeb service settings:

- `SECRET_KEY`
  - Must be a long random value (32+ bytes).
- `DATABASE_URL`
  - Must be async SQLAlchemy DSN, e.g.:
  - `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME`
- `ALLOWED_ORIGINS`
  - JSON list string, for example:
  - `["https://your-app-domain.koyeb.app"]`

Recommended:
- `ACCESS_TOKEN_EXPIRE_MINUTES=60`
- `ALGORITHM=HS256`

Optional (AI final report):
- `GOOGLE_API_KEY`
- `GEMINI_MODEL=gemini-1.5-flash`

Optional (email login notification):
- `SMTP_HOST`
- `SMTP_PORT=587`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`

## 3) Create Service on Koyeb

1. Open: [Koyeb - Create Service](https://app.koyeb.com/services/new)
2. Select **GitHub** deployment source.
3. Choose repository + branch.
4. Build method:
   - Keep **Dockerfile** build.
5. Port:
   - Set/confirm container port `8000`.
6. Start command:
   - Keep Docker default:
   - `uvicorn main:app --host 0.0.0.0 --port 8000`
7. Add all env vars from section 2.
8. Deploy.

## 4) Database Notes (Critical)

- Do **not** use SQLite in Koyeb production.
- Use managed PostgreSQL and correct async DSN.
- Validate DB connectivity with:
  - `GET /ready`

Current app behavior:
- On startup, app initializes schema from SQLAlchemy metadata.
- If you later add strict migrations, add Alembic migration run step before app startup.

## 5) Do You Need to Build Docker Image Manually?

- **No** for normal GitHub -> Koyeb flow.
- Koyeb builds image from your `Dockerfile`.

Manual image build/push is only needed if you deploy from container registry directly.

## 6) WebSocket Deployment Notes

Your app uses:
- `/ws/ue5/{session_id}`
- `/ws/dashboard/{session_id}`

Checklist:
- Use service public URL as WS host.
- Browser dashboard should use `wss://` in production (handled by frontend protocol logic).
- Ensure JWT auth works for both REST and WS handshake.
- Ensure `ALLOWED_ORIGINS` includes your deployed frontend origin.

## 7) Post-Deploy Validation Checklist

1. Health checks:
   - `GET /health` -> `{"status":"ok", ...}`
   - `GET /ready` -> DB ready response
2. Auth:
   - Register -> Login -> `/api/auth/me`
3. Core data:
   - Create patient
   - Start session using access key
4. Live flow:
   - Connect dashboard session page
   - Send simulator data (or UE5 data)
   - Verify charts + state updates + commands
5. AI report:
   - Call `POST /api/sessions/{id}/report`
   - Fetch with `GET /api/sessions/{id}/report`
   - Verify fallback works if Gemini key is missing

## 8) Common Problems and Fixes

- App fails at startup:
  - Missing `SECRET_KEY` or malformed `DATABASE_URL`.
- `/ready` returns 500:
  - DB unreachable, wrong host/port/credentials, or network policy issue.
- CORS errors:
  - `ALLOWED_ORIGINS` missing deployed frontend domain.
- WS disconnect/auth issues:
  - Invalid JWT
  - Wrong session ownership
  - `ws://` used instead of `wss://` on HTTPS site
- Static pages not loading:
  - Check app root route and `/static` path availability.

## 9) Security Hardening Before Public Demo

- Rotate all secrets (especially any previously exposed API key).
- Keep `.env` out of git; commit only `.env.example`.
- Shorten token lifetime for production.
- Disable WS query-token fallback in production mode (keep subprotocol auth only).
- Restrict CORS to exact domains.
