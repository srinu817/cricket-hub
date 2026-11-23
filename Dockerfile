FROM node:22-alpine AS frontend-build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.13-slim AS application

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini ./
COPY --from=frontend-build /app/dist ./dist

RUN groupadd --system app && useradd --system --gid app --create-home app
USER app

EXPOSE 8787
CMD ["sh", "-c", "python -m alembic upgrade head && python -m backend.scripts.import_verified_cricket_batch_1 && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8787"]
