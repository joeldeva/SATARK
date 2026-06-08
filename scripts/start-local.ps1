$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root "apps/api"
$web = Join-Path $root "apps/web"

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

Start-Process -FilePath python -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001") -WorkingDirectory $api -WindowStyle Hidden

$env:VITE_API_URL = "/api"
Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "--port", "3001") -WorkingDirectory $web -WindowStyle Hidden

Write-Host "SATARK API: http://localhost:8001"
Write-Host "SATARK Web: http://localhost:3001"
