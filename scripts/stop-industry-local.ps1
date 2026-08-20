$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "Stopping RepoGuardian industry-local services started by local ports"

foreach ($port in 3000, 8000) {
  $rows = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($processId in ($rows | Select-Object -ExpandProperty OwningProcess -Unique)) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    if ($process -and ($process.CommandLine -match "RepoGuardian")) {
      Write-Host "Stopping process $processId on port $port"
      Stop-Process -Id $processId -ErrorAction SilentlyContinue
    } else {
      Write-Host "Leaving process $processId on port $port untouched; command line did not match RepoGuardian."
    }
  }
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker compose -f "$Root\docker-compose.production.yml" stop worker backend frontend postgres redis
} else {
  Write-Host "Docker is not installed; no compose services stopped."
}
