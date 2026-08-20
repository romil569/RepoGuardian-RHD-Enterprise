# Deployment

Deployment status: `DEPLOYMENT_READY_NOT_PROVISIONED`

RepoGuardian now includes container and compose foundations, but no cloud infrastructure has been provisioned.

## Local Demo

```powershell
.\scripts\start-dev.ps1
```

## Production Compose Skeleton

```powershell
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up
```

Docker Desktop is required for the local production stack. If Docker is unavailable, use lightweight mode with SQLite/local vectors.

Required production variables:

- `POSTGRES_PASSWORD`
- `FRONTEND_URL`
- provider keys if cloud AI is enabled
- GitHub App settings if using app authentication

## Managed Platform Requirements

- PostgreSQL with pgvector
- Redis
- HTTPS backend URL
- frontend environment variable `NEXT_PUBLIC_API_BASE_URL`
- secret manager for GitHub and model provider credentials

Do not run production writes without configuring human approval and policy allow-lists.

## Terraform

Validated locally:

- `terraform fmt -check`
- `terraform init -backend=false`
- `terraform validate`

No `terraform apply` has been run.
