# syntax=docker/dockerfile:1

# --- Next.js static export (サービス画面) ---
FROM node:22-alpine AS web-builder
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
ENV NEXT_PUBLIC_API_BASE_URL=
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- FastAPI + static UI ---
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    CORS_ORIGINS=* \
    WEB_BASE_URL=

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ .
COPY --from=web-builder /web/out /app/web_static

RUN test -f /app/web_static/index.html \
    && python -c "from app.main import app; print('import-ok', app.title)"

EXPOSE 5000

CMD ["sh", "-c", "echo \"[elearning] binding 0.0.0.0:${PORT:-5000}\" && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-5000}"]
