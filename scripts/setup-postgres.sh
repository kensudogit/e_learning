#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Starting PostgreSQL..."
docker compose up -d db

echo "==> Waiting for health..."
until docker compose exec -T db pg_isready -U elearning -d elearning >/dev/null 2>&1; do
  sleep 1
done

echo "==> Applying schema..."
docker compose exec -T db psql -U elearning -d elearning < sql/001_schema.sql

echo "==> Tables:"
docker compose exec -T db psql -U elearning -d elearning -c '\dt'

echo "PostgreSQL ready: postgresql+asyncpg://elearning:elearning@localhost:5433/elearning"
