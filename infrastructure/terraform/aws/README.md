# RepoGuardian AWS Terraform Skeleton

This folder documents the intended production infrastructure boundary. It is intentionally minimal until a target AWS account, network, domain, and secret manager policy are selected.

Planned resources:

- VPC, private subnets, and security groups
- ECS or Kubernetes runtime for backend, worker, and frontend containers
- RDS PostgreSQL with pgvector enabled
- ElastiCache Redis for queued jobs
- Secrets Manager for GitHub App and model provider credentials
- Application Load Balancer and TLS certificate
- CloudWatch logs, metrics, and alarms

Local demo execution does not require Terraform.
