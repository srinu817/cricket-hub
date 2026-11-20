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
python -m pip install -r requirements-dev.txt
npm install
$env:CRICKET_ADMIN_EMAIL = "your-admin@example.com"
$env:CRICKET_ADMIN_PASSWORD = "use-a-long-unique-password"
$env:CRICKET_APP_ORIGIN = "http://127.0.0.1:5173"
npm run start
```

Open `http://127.0.0.1:5173` and sign in at `/admin`. The API creates the local SQLite schema on startup and stores data in `data/cricket_hub.db`. `npm run start` launches the FastAPI and Vite development servers together. They can also be started separately with `npm run api` and `npm run dev`.

## Docker deployment

Docker and Docker Compose are required. The Compose stack builds the React site into the FastAPI image, runs PostgreSQL, applies Alembic migrations, and serves the site and API from one origin.

```powershell
Copy-Item .env.example .env
notepad .env
docker compose up --build -d
docker compose logs -f app
```

Replace every example password in `.env`. Set `CRICKET_APP_ORIGIN` to the exact public origin, such as `https://cricket.example.com`, and set `APP_ENV=production` when HTTPS is enabled so the admin cookie uses the `Secure` attribute. The database is stored in the `postgres_data` named volume. Do not commit `.env`; keep the database password and admin credentials in the deployment platform's secret manager.

The API health check is `/api/v1/health`. OpenAPI documentation is available at `/docs`.

## API

- `GET /api/v1/matches` and `GET /api/v1/matches/{id}` are public.
- `POST /api/v1/auth/login`, `GET /api/v1/auth/session`, and `POST /api/v1/auth/logout` handle admin sessions.
- `POST`, `PUT`, and `DELETE /api/v1/matches[/{id}]` require an admin session.
- Match scorecards support up to four innings, batting and bowling figures, and commentary.

## Tests and checks

```powershell
python -m pytest -q
python -m alembic upgrade head
npm run build
```

The GitHub Actions workflow runs the Python tests and frontend build on pushes and pull requests.

## Deployment notes

The app and in-memory admin sessions are designed for a single application instance. Use a persistent PostgreSQL service, backups, HTTPS, and strong secret values. For multi-instance scaling, move sessions to a shared store and configure login rate limiting. Cricket match and scorecard information must be entered by an administrator; no external provider integration is included.
