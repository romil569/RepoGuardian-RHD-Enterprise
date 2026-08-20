$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot

function Status($Name, $Status, $Detail = "") {
  "{0,-30} {1,-14} {2}" -f $Name, $Status, $Detail
}

function Command-Status($Name, $Command, [string[]]$CommandArgs = @("--version")) {
  $cmd = Get-Command $Command -ErrorAction SilentlyContinue
  if (-not $cmd) {
    Status $Name "MISSING" "not on PATH"
    return
  }
  $detail = try { (& $Command @CommandArgs 2>&1 | Select-Object -First 1 | Out-String).Trim() } catch { $_.Exception.Message }
  Status $Name "OK" $detail
}

function Terraform-Status {
  $terraform = Get-Command terraform -ErrorAction SilentlyContinue
  if ($terraform) {
    Command-Status "Terraform" terraform @("version")
    return
  }

  $wingetTerraform = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter terraform.exe -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($wingetTerraform) {
    $detail = try { (& $wingetTerraform.FullName version 2>&1 | Select-Object -First 1 | Out-String).Trim() } catch { $_.Exception.Message }
    Status "Terraform" "OK" "$detail (installed; restart shell for PATH)"
  } else {
    Status "Terraform" "MISSING" "not on PATH"
  }
}

function Env-Configured($Name) {
  $value = [Environment]::GetEnvironmentVariable($Name)
  if ($value) { Status $Name "CONFIGURED" "value hidden" } else { Status $Name "NOT_SET" "optional unless enabled" }
}

function Http-Status($Name, $Url) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 $Url
    Status $Name "OK" "HTTP $($response.StatusCode)"
  } catch {
    Status $Name "UNREACHABLE" $_.Exception.Message
  }
}

function Port-Status($Name, $Port) {
  $rows = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($rows) {
    $pids = ($rows | Select-Object -ExpandProperty OwningProcess -Unique) -join ","
    Status $Name "LISTENING" "port $Port pid $pids"
  } else {
    Status $Name "STOPPED" "port $Port"
  }
}

Write-Host "RepoGuardian RHD doctor"
Write-Host "Root: $Root"
Write-Host ""

Command-Status "Git" git @("--version")
Command-Status "GitHub CLI" gh @("--version")
Command-Status "Python" python @("--version")
Command-Status "Node.js" node @("--version")
Command-Status "npm" npm @("--version")
Command-Status "Docker" docker @("--version")
Command-Status "Docker Compose" docker @("compose", "version")
Terraform-Status
Command-Status "Ollama" ollama @("--version")

$dockerService = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
if ($dockerService) { Status "Docker Desktop service" $dockerService.Status "com.docker.service" } else { Status "Docker Desktop service" "MISSING" "Docker Desktop not installed" }

Write-Host ""
Write-Host "Configuration"
Env-Configured "GITHUB_TOKEN"
Env-Configured "GITHUB_APP_ID"
Env-Configured "GITHUB_APP_INSTALLATION_ID"
Env-Configured "GITHUB_WEBHOOK_SECRET"
Env-Configured "OLLAMA_MODEL"
Env-Configured "GROQ_API_KEY"
Env-Configured "OPENROUTER_API_KEY"
Env-Configured "OPENAI_API_KEY"

Write-Host ""
Write-Host "Runtime"
Port-Status "Frontend" 3000
Port-Status "Backend" 8000
Port-Status "PostgreSQL" 5432
Port-Status "Redis" 6379
Port-Status "Ollama API" 11434
Http-Status "Backend health" "http://127.0.0.1:8000/health"
Http-Status "Model gateway" "http://127.0.0.1:8000/api/platform/model-gateway"
Http-Status "ML registry" "http://127.0.0.1:8000/api/platform/ml-models"

Write-Host ""
Write-Host "Local files"
if (Test-Path "$Root\backend\.venv\Scripts\python.exe") { Status "Backend venv" "OK" "backend\.venv" } else { Status "Backend venv" "MISSING" "run backend setup" }
if (Test-Path "$Root\frontend\node_modules") { Status "Frontend node_modules" "OK" "frontend\node_modules" } else { Status "Frontend node_modules" "MISSING" "run npm install" }
if (Test-Path "$Root\infrastructure\terraform\aws\.terraform.lock.hcl") { Status "Terraform lock" "OK" "provider initialized" } else { Status "Terraform lock" "MISSING" "run terraform init -backend=false" }
