$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$ExternalEnv = Join-Path (Split-Path -Parent $Root) "RepoGuardian.env"

function Test-Command($Name) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if ($cmd) { "OK $Name -> $($cmd.Source)" } else { "MISSING $Name" }
}

Write-Host "RepoGuardian doctor"
Write-Host "Root: $Root"
Test-Command git
Test-Command gh
Test-Command python
Test-Command node
Test-Command npm
Test-Command docker

Write-Host "`nGitHub authentication:"
gh auth status

Write-Host "`nPython backend:"
if (Test-Path "$Root\backend\.venv\Scripts\python.exe") {
  & "$Root\backend\.venv\Scripts\python.exe" --version
} else {
  Write-Host "MISSING backend virtualenv"
}

Write-Host "`nFrontend dependencies:"
if (Test-Path "$Root\frontend\node_modules") { Write-Host "OK node_modules present" } else { Write-Host "MISSING frontend node_modules" }

Write-Host "`nPorts:"
foreach ($port in 3000, 8000, 5432) {
  $rows = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
  if ($rows) {
    $rows | Select-Object LocalAddress, LocalPort, State, OwningProcess | Format-Table
  } else {
    Write-Host "FREE $port"
  }
}

Write-Host "`nAI provider:"
if ($env:OPENAI_API_KEY) {
  Write-Host "OPENAI_API_KEY configured in environment"
} elseif ((Test-Path $ExternalEnv) -and (Select-String -Path $ExternalEnv -Pattern '^OPENAI_API_KEY\s*=\s*\S+' -Quiet)) {
  Write-Host "OPENAI_API_KEY configured in external RepoGuardian.env"
} elseif ((Test-Path "$Root\backend\.env") -and (Select-String -Path "$Root\backend\.env" -Pattern '^OPENAI_API_KEY\s*=\s*\S+' -Quiet)) {
  Write-Host "OPENAI_API_KEY configured in backend .env"
} else {
  Write-Host "OPENAI_API_KEY not configured; deterministic intelligence remains active"
}
