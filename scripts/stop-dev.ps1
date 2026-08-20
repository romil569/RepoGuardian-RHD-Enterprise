$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Split-Path -Parent $PSScriptRoot)).Path

Write-Host "Stopping RepoGuardian dev processes launched from this workspace"
$processes = Get-CimInstance Win32_Process | Where-Object {
  ($_.CommandLine -match [regex]::Escape($Root)) -and
  (($_.CommandLine -match "uvicorn app.main:app") -or ($_.CommandLine -match "next dev") -or ($_.CommandLine -match "npm run dev"))
}

foreach ($process in $processes) {
  Write-Host "Stopping PID $($process.ProcessId): $($process.CommandLine)"
  Stop-Process -Id $process.ProcessId -Force
}

if (!$processes) {
  Write-Host "No matching RepoGuardian dev processes found."
}
