$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root "apps/api"
$web = Join-Path $root "apps/web"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required for SATARK backend services: Postgres, Redis, and Chroma."
}

Push-Location $root
try {
    & docker compose up -d postgres redis chroma
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed to start required SATARK services"
    }
}
finally {
    Pop-Location
}

$model = "gemma2:2b"
$modelList = & ollama list 2>$null
if ($LASTEXITCODE -ne 0 -or ($modelList -notmatch [regex]::Escape($model))) {
    Write-Host "Pulling local LLM model $model..."
    & ollama pull $model
}

$env:LLM_PROVIDER = "ollama"
$env:LLM_MODEL = $model
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:LLM_REQUIRED = "true"
$env:DATABASE_URL = "postgresql+psycopg://satark:satark@127.0.0.1:5432/satark"
$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:CHROMA_URL = "http://127.0.0.1:8002"

Push-Location $api
try {
    & python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic migration failed"
    }
}
finally {
    Pop-Location
}

Start-Process -FilePath python -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001") -WorkingDirectory $api -WindowStyle Hidden

$env:VITE_API_URL = "/api"
Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "--port", "3001") -WorkingDirectory $web -WindowStyle Hidden

Write-Host "SATARK API: http://localhost:8001"
Write-Host "SATARK Web: http://localhost:3001"
