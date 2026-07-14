# eラーニング統合プラットフォーム — 開発起動 (Windows PowerShell)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "==> Starting infrastructure (db, redis)..."
docker compose up -d db redis

Write-Host "==> Waiting for Postgres..."
do {
  Start-Sleep -Seconds 1
  $ready = docker compose exec -T db pg_isready -U elearning -d elearning 2>$null
} while ($LASTEXITCODE -ne 0)

Write-Host "==> Done."
Write-Host "  Backend:  cd apps\api; py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn app.main:app --reload"
Write-Host "  Frontend: cd apps/web; npm install; npm run dev"
Write-Host "  Or all:   docker compose up --build"
