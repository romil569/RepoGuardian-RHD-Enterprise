$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$ExternalEnv = Join-Path (Split-Path -Parent $Root) "RepoGuardian.env"

function Import-EnvFile($Path) {
  if (!(Test-Path $Path)) { return }
  Get-Content $Path | ForEach-Object {
    $line = $_.Trim()
    if ($line -and !$line.StartsWith("#") -and $line.Contains("=")) {
      $name, $value = $line.Split("=", 2)
      if ($name) {
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
      }
    }
  }
  Write-Host "Loaded local environment overrides from $Path"
}

Write-Host "Starting RepoGuardian development services"
Import-EnvFile $ExternalEnv

if (Get-Command docker -ErrorAction SilentlyContinue) {
  Write-Host "Docker detected. PostgreSQL can be started manually with: docker compose up -d postgres"
} else {
  Write-Host "Docker unavailable. Using SQLite/local vector fallback."
}

$backendPython = Join-Path $Backend ".venv\Scripts\python.exe"
if (!(Test-Path $backendPython)) {
  throw "Backend virtualenv not found. Run: cd backend; python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements.txt"
}
if (!(Test-Path (Join-Path $Frontend "node_modules"))) {
  throw "Frontend dependencies not found. Run: cd frontend; npm install"
}

$backendListening = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if (!$backendListening) {
  Start-Process -FilePath $backendPython -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $Backend -WindowStyle Hidden
  Write-Host "Backend starting at http://127.0.0.1:8000"
} else {
  Write-Host "Backend port 8000 already in use; leaving existing process untouched."
}

$frontendListening = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if (!$frontendListening) {
  Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $Frontend -WindowStyle Hidden
  Write-Host "Frontend starting at http://127.0.0.1:3000"
} else {
  Write-Host "Frontend port 3000 already in use; leaving existing process untouched."
}

Write-Host "Open http://127.0.0.1:3000"
