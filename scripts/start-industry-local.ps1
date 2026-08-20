$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot

function Ensure-Port-Free($Port, $Name) {
  $rows = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($rows) {
    Write-Host "$Name already appears to be listening on port $Port. Leaving it untouched."
    return $false
  }
  return $true
}

Write-Host "Starting RepoGuardian industry-local mode"
Write-Host "Root: $Root"

if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker compose -f "$Root\docker-compose.production.yml" up -d postgres redis
} else {
  Write-Host "Docker is not installed; PostgreSQL/Redis startup skipped."
}

if (Get-Command ollama -ErrorAction SilentlyContinue) {
  try {
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:11434/api/tags | Out-Null
    Write-Host "Ollama API reachable."
  } catch {
    Write-Host "Ollama command exists, but API is not reachable. Start Ollama from Windows before live local AI validation."
  }
} else {
  Write-Host "Ollama is not installed; deterministic fallback remains available."
}

if (Ensure-Port-Free 8000 "Backend") {
  Start-Process -WindowStyle Hidden -FilePath "$Root\backend\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory "$Root\backend"
}

if (Ensure-Port-Free 3000 "Frontend") {
  Start-Process -WindowStyle Hidden -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory "$Root\frontend"
}

Write-Host "Industry-local start attempted. Run scripts\doctor.ps1 for current status."
