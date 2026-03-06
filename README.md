# AI Presentation Generator (neko.ai)

AI-powered presentation generator with session-based editing, user auth, provider failover (Groq → Gemini), and polished UI.

## Highlights

- AI generation with automatic provider fallback (`Groq` primary, `Gemini` secondary)
- Email OTP signup + password login + Google sign-in
- Per-user presentation history (download + delete)
- Slide-level editing with version history
- Themed PPT output via `python-pptx`
- Async job-based generation with progress polling
- Slide-based usage quota (currently enforced at total 50 slides/user)

## Tech Stack

- Frontend: `React 18`, `Vite`, `Axios`, `lucide-react`
- Backend: `FastAPI`, `SQLAlchemy (async)`, `SQLite`, `python-pptx`
- AI Providers: `Groq`, `Google Gemini`

## Security Note

- Do not commit real credentials, API keys, SMTP passwords, or tokens to Git.
- Keep production secrets only in your deployment platform environment settings.
- Treat `.env` files as local-only and ensure they are ignored by Git.

## Prerequisites

- Python `3.10+` (project currently uses `3.12` venv)
- Node.js `18+`
- At least one AI key: `GROQ_API_KEY` and/or `GEMINI_API_KEY`

## Setup

### 1) Backend

```bash
cd backend

# If you use the repository venv:
# Windows PowerShell
..\ppt_env\Scripts\Activate.ps1

# Install deps (if not already installed)
pip install -r requirements.txt

# Create env file
copy .env.example .env
```

Set in `backend/.env`:

```env
GROQ_API_KEY=...
GEMINI_API_KEY=...

AUTH_SECRET=...
GOOGLE_CLIENT_ID=...

# OTP + email verification
OTP_SECRET=...
OTP_TTL_SECONDS=600
OTP_MAX_ATTEMPTS=5
OTP_RESEND_COOLDOWN_SECONDS=45
PENDING_SIGNUP_TTL_SECONDS=1800
SIGNUP_TOKEN_TTL_SECONDS=1800

# SMTP (required for production OTP emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=...
SMTP_FROM_NAME=AI PPT
SMTP_USE_TLS=true

# Optional disposable-email provider API
DISPOSABLE_EMAIL_API_URL=
DISPOSABLE_EMAIL_API_KEY=

# Dev only: return OTP in API response if SMTP is not configured
AUTH_DEBUG_RETURN_OTP=false
```

Run backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env` (or use `.env.example`):

```env
VITE_GOOGLE_CLIENT_ID=...
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Run frontend:

```bash
npm run dev
```

Open: `http://127.0.0.1:5173`

## Deploy Frontend on Vercel

1. Import this repo in Vercel.
2. Set **Root Directory** to `frontend`.
3. Framework preset: `Vite`.
4. Add environment variables:
	- `VITE_GOOGLE_CLIENT_ID`
	- `VITE_API_BASE_URL` = `https://<your-render-backend>.onrender.com/api`
5. Deploy.
6. Add your Vercel URL to backend `CORS_ORIGINS` and redeploy backend.

## OAuth Notes (Google)

In Google Cloud OAuth settings, add exact origins used in dev:

- `http://127.0.0.1:5173`
- `http://localhost:5173` (if you also use localhost)

Origin mismatch is strict.

## API Access

- API routes are available under `/api` after backend startup.
- For local verification, use `/health` and `/api/ai/status`.

## Testing & Validation

There is currently no dedicated unit/integration test suite in this repo. Recommended validation commands:

### Frontend

```bash
cd frontend
npm run build
```

### Backend

```bash
cd backend
python -m compileall app
```

### Runtime smoke checks

```bash
# health
curl http://127.0.0.1:8000/health

# provider status
curl http://127.0.0.1:8000/api/ai/status
```

## Troubleshooting

### Vite proxy `ECONNREFUSED`

- Ensure backend is running on `127.0.0.1:8000`
- Ensure Vite proxy target points to `127.0.0.1` (not only `localhost`)

### Google prompt blocked/unavailable

- Allow popups and third-party cookies
- Check exact OAuth origin registration

### Provider unavailable

- Verify keys in `backend/.env`
- Check `/api/ai/status` response

## Deploy Backend on Render

### Option A: Blueprint (recommended)

1. Push this repo to GitHub (already done).
2. In Render, choose **New +** → **Blueprint**.
3. Select this repository; Render will detect `render.yaml`.
4. Set secret env vars in Render dashboard:
	- `DATABASE_URL` (Neon connection string: `postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME?ssl=require`)
	- `AUTH_SECRET`
	- `GROQ_API_KEY` and/or `GEMINI_API_KEY`
	- `GOOGLE_CLIENT_ID` (if using Google auth)
5. Update `CORS_ORIGINS` to your deployed frontend URL(s), comma-separated.

### Option B: Manual Web Service

- Root Directory: `backend`
- Environment: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Python Version env: `PYTHON_VERSION=3.11.9`

### Notes

- Current default DB is SQLite in `backend/storage/ai_ppt.db`.
- For Neon (recommended), create a Neon Postgres project and set Render `DATABASE_URL` to:
	- `postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME?ssl=require`
- With Neon `DATABASE_URL`, no Render persistent disk is required for the database.

## Roadmap Suggestions

- Split `backend/app/api/routes.py` into domain routers (`auth`, `history`, `generation`, `slides`)
- Add automated tests (`pytest` + API integration tests)
- Add CI workflow for build/smoke checks
