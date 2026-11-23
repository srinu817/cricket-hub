# Cricket Hub

Cricket Hub is a React + FastAPI application for administrator-entered match schedules, results, scorecards, and commentary. It does not claim to show live scores or data from a cricket provider.

## Stack

- React, TypeScript, Vite
- FastAPI, Pydantic, SQLAlchemy 2, Alembic
- SQLite for local development; PostgreSQL for Docker deployment
- HTTP-only, same-site admin session cookies

## Run locally

Requirements: Node.js 22, Python 3.13, and npm.

In PowerShell, from the project directory:

```powershell
Copy-Item .env.example .env
notepad .env
# Set CRICKET_ADMIN_PASSWORD to your own 12+ character password, then save.
python -m pip install -r requirements-dev.txt
npm install
npm run start
```

Open `http://127.0.0.1:5173` and sign in at `/admin`. On first startup, the API creates exactly one admin row from `CRICKET_ADMIN_EMAIL` and `CRICKET_ADMIN_PASSWORD`; the database stores a salted PBKDF2 hash, not the password. There is intentionally no public signup route. The environment values also rotate that single seeded admin on a later startup.

Use the email `admin@crickethub.com` if desired, but choose your own strong password of at least 12 characters. The suggested `admin@123` is too weak and is not included in the repository or database seed. The API creates the local SQLite schema on startup and stores match data in `data/cricket_hub.db`. `npm run start` launches the FastAPI and Vite development servers together. They can also be started separately with `npm run api` and `npm run dev`.

## Docker deployment

Docker and Docker Compose are required. The Compose stack builds the React site into the FastAPI image, runs PostgreSQL, applies Alembic migrations, and serves the site and API from one origin.

```powershell
Copy-Item .env.example .env
notepad .env
docker compose up --build -d
docker compose logs -f app
```

Set a unique `POSTGRES_PASSWORD` and an admin password of at least 12 characters in `.env`. Set `CRICKET_APP_ORIGIN` to the exact public origin, such as `https://cricket.example.com`, and set `APP_ENV=production` when HTTPS is enabled so the admin cookie uses the `Secure` attribute. The database is stored in the `postgres_data` named volume. Do not commit `.env`; keep the database password and admin credentials in the deployment platform's secret manager.

The API health check is `/api/v1/health`. OpenAPI documentation is available at `/docs`.

## Render deployment (backend API)

Create a Render **Python Web Service** from the repository. Keep **Root Directory** blank (the repository root), so Python can import the `backend` package and Alembic can find `alembic.ini`.

Use these commands:

```text
Build Command: pip install -r requirements.txt
Start Command: python -m alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

The application variable is `app` in `backend/app/main.py`. Do not use `uvicorn main:app`: there is no repository-root `main.py`, and when the service root is set to `backend/app`, the parent `backend` package is no longer importable.

Add these environment variables in Render:

- `DATABASE_URL`: the Render PostgreSQL connection URL. The app converts standard `postgres://` and `postgresql://` URLs to the installed `psycopg` v3 driver.
- `CRICKET_ADMIN_EMAIL`: the admin sign-in email.
- `CRICKET_ADMIN_PASSWORD`: a strong password of at least 12 characters.
- `CRICKET_APP_ORIGIN`: the exact public service origin, such as `https://your-service.onrender.com`.
- `APP_ENV`: `production`, so admin session cookies are marked secure.

Do not omit `DATABASE_URL` on Render: without it, the app falls back to local SQLite, which is not durable on a hosted service. Migrations run at startup before the app bootstraps the admin account. This Python service serves the API; it will not include the React site unless the frontend is built into `dist` as in the Docker deployment.

### Loading verified cricket data

The verified fixture seed is deliberately separate from application startup. After
deploying migrations, run this command once against the same `DATABASE_URL` used
by the deployed service:

```text
python -m backend.scripts.import_verified_cricket_batch_1
```

The script is idempotent: it creates only missing teams, series relationships,
and matches, so it is safe to rerun. It uses PostgreSQL automatically when the
deployment has `DATABASE_URL` set; otherwise it uses the local SQLite fallback.

## API

- `GET /api/v1/matches` and `GET /api/v1/matches/{id}` are public.
- `POST /api/v1/auth/login`, `GET /api/v1/auth/session`, and `POST /api/v1/auth/logout` handle admin sessions.
- `POST`, `PUT`, and `DELETE /api/v1/matches[/{id}]` require an admin session.
- Match scorecards support up to four innings, batting and bowling figures, and commentary.
- Admin master-data endpoints require an admin session: `GET`/`POST /api/v1/admin/teams`, `GET`/`POST /api/v1/admin/players`, and `GET`/`POST /api/v1/admin/series`, with `PUT /api/v1/admin/{teams|players|series}/{id}` for updates. List endpoints support `q`, `limit`, and `offset`.
- Manage teams, players, and series from the admin navigation, then select those records in the match editor. Use `isActive` to deactivate a master instead of deleting it. Existing match and scorecard text remains the public snapshot; historical text is not automatically linked to new masters.
- The additive master-data schema migration is `d3a9c1e7f421_add_reusable_master_data.py`. The Render start command above runs `python -m alembic upgrade head` before starting FastAPI.

## Tests and checks

```powershell
python -m pytest -q
python -m alembic upgrade head
npm run build
```

The GitHub Actions workflow runs the Python tests and frontend build on pushes and pull requests.

## Deployment notes

The app and in-memory admin sessions are designed for a single application instance. Use a persistent PostgreSQL service, backups, HTTPS, and strong secret values. For multi-instance scaling, move sessions to a shared store and configure login rate limiting. Cricket match and scorecard information must be entered by an administrator; no external provider integration is included.
