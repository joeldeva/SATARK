$ErrorActionPreference = "Stop"

$envPath = Join-Path $PSScriptRoot ".env"
$examplePath = Join-Path $PSScriptRoot ".env.example"

if (-not (Test-Path $examplePath)) {
  throw "Missing .env.example in apps/whatsapp"
}

Copy-Item -LiteralPath $examplePath -Destination $envPath -Force
Write-Host "Created apps/whatsapp/.env for deployed SATARK backend."
Write-Host "Backend: https://satark-api.onrender.com"
Write-Host "Run: npm install; npm run dev"
