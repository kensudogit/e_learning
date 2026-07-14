# PostgreSQL setup (Docker)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "==> Starting PostgreSQL container..."
docker compose up -d db

Write-Host "==> Waiting for healthy..."
do {
  Start-Sleep -Seconds 1
  docker compose exec -T db pg_isready -U elearning -d elearning | Out-Null
} while ($LASTEXITCODE -ne 0)

Write-Host "==> Applying schema (sql/001_schema.sql)..."
Get-Content -Raw .\sql\001_schema.sql | docker compose exec -T db psql -U elearning -d elearning

Write-Host "==> Listing tables..."
docker compose exec -T db psql -U elearning -d elearning -c "\dt"

Write-Host ""
Write-Host "PostgreSQL is ready"
Write-Host "  Host: localhost"
Write-Host "  Port: 5433"
Write-Host "  DB:   elearning"
Write-Host "  User: elearning / elearning"
Write-Host "  URL:  postgresql+asyncpg://elearning:elearning@localhost:5433/elearning"
Write-Host ""
Write-Host "Note: Docker maps to 5433 to avoid conflict with local PostgreSQL on 5432."
