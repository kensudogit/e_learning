#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Starting infrastructure (db, redis)..."
docker compose up -d db redis

echo "==> Waiting for Postgres..."
until docker compose exec -T db pg_isready -U elearning -d elearning >/dev/null 2>&1; do
  sleep 1
done

echo "==> Done. Next steps:"
echo "  Backend:  cd apps/api && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload"
echo "  Frontend: cd apps/web && npm install && npm run dev"
echo "  Or all:   docker compose up --build"
