$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root "apps/api"
$web = Join-Path $root "apps/web"

$modelList = & ollama list 2>$null
if ($LASTEXITCODE -ne 0 -or ($modelList -notmatch "llama3\.2:3b")) {
    Write-Host "Pulling local LLM model llama3.2:3b..."
    & ollama pull llama3.2:3b
}

$env:LLM_PROVIDER = "ollama"
$env:LLM_MODEL = "llama3.2:3b"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:LLM_REQUIRED = "true"

Start-Process -FilePath python -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001") -WorkingDirectory $api -WindowStyle Hidden

$env:VITE_API_URL = "/api"
Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "--port", "3001") -WorkingDirectory $web -WindowStyle Hidden

Write-Host "SATARK API: http://localhost:8001"
Write-Host "SATARK Web: http://localhost:3001"
