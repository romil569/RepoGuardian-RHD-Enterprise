# RepoGuardian RHD Activation Preflight

Collected on 2026-08-20 from `C:\Users\HP\Desktop\RepoGuardian`.

| Tool | Version / Detection | Status | Required Action |
|---|---|---|---|
| Git | `git version 2.54.0.windows.1` | WORKING | None |
| GitHub CLI | `gh version 2.97.0 (2026-07-31)` | WORKING | None |
| Python | `Python 3.12.10` | WORKING | None |
| Backend venv Python | `Python 3.12.10` | WORKING | None |
| pip | `pip 26.2.1` in backend venv | WORKING | None |
| Node.js | `v24.19.0` | WORKING | None |
| npm | `11.17.0` | WORKING | None |
| Docker CLI | `docker` not found | NOT_INSTALLED | Install Docker Desktop; GUI/admin/restart may be required |
| Docker Compose | `docker` not found | NOT_INSTALLED | Install Docker Desktop with Compose plugin |
| Docker Desktop service | `com.docker.service` not found | NOT_INSTALLED | Install Docker Desktop |
| Terraform | Installed via winget as `Terraform v1.15.8`; current shell may need restart for PATH | WORKING | None; direct winget path used for validation |
| Ollama | `ollama version is 0.32.13`; API reachable on `127.0.0.1:11434` | WORKING | None |
| PowerShell | `7.6.4` | WORKING | None |
| winget | `v1.29.280` | WORKING | None |
| curl | `curl 8.21.0` | WORKING | None |
| Available RAM | 9.17 GB free / 23.02 GB total | INFO | Suitable for local development; choose modest local model |
| Free disk C: | 126.19 GB free / 464.54 GB total | INFO | Enough for Docker images and one modest Ollama model |
| GPU | AMD Radeon 860M Graphics; NVIDIA GeForce RTX 5050 Laptop GPU | INFO | NVIDIA acceleration may be available |
| NVIDIA SMI / CUDA | NVIDIA GeForce RTX 5050 Laptop GPU, 8151 MiB VRAM, driver 592.19 | WORKING | Select a model that fits 8 GB VRAM |

## Baseline Validation

Starting commit: `23cd02d`

Starting tag: `industry-rhd-v1`

Backup branch: `activation-backup-industry-rhd-v1`

Baseline checks:

| Check | Result |
|---|---|
| Backend tests | `46 passed` |
| Frontend lint | PASS |
| Frontend typecheck | PASS |
| Frontend build | PASS |

## Immediate Blockers

- Docker/PostgreSQL/pgvector/Redis production validation is blocked until Docker Desktop is installed and running.
- Terraform validation is complete: `fmt -check`, `init -backend=false`, and `validate` passed for `infrastructure/terraform/aws`.
- Ollama local provider validation completed with `qwen3:1.7b`; the direct probe succeeded in 38.9s and the FastAPI gateway probe succeeded in 15.6s, so it is functional but slow.
- `qwen3:8b` was pulled but did not complete simple probes within 45-120s on this machine, so it is not the active demo model.
- Cloud provider validation is optional and depends on local environment keys; API keys must not be pasted into chat.

## Terraform Validation

Terraform was installed with:

```powershell
winget install Hashicorp.Terraform --silent --accept-source-agreements --accept-package-agreements
```

Validation commands completed successfully:

```powershell
terraform -chdir=infrastructure\terraform\aws fmt -check
terraform -chdir=infrastructure\terraform\aws init -backend=false
terraform -chdir=infrastructure\terraform\aws validate
```

No `plan` or `apply` was run. No cloud infrastructure was provisioned.

## Ollama Validation

Models pulled locally:

| Model | Status | Evidence |
|---|---|---|
| `qwen3:1.7b` | VALIDATED | `/api/generate` returned expected text in 38.9s; `/api/platform/model-gateway/probe` returned provider `ollama` in 15.6s |
| `qwen3:8b` | INSTALLED_NOT_DEMO_READY | Simple probes timed out at 45-120s |

The application default was switched to `OLLAMA_MODEL=qwen3:1.7b` for local activation.
