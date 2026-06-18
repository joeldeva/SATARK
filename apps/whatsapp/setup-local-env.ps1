$source = Join-Path $PSScriptRoot ".env.local.example"
$target = Join-Path $PSScriptRoot ".env"

if (!(Test-Path $source)) {
  throw "Missing .env.local.example in apps/whatsapp"
}

Copy-Item $source $target -Force
Write-Host "Created apps/whatsapp/.env for local SATARK backend."
