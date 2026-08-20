terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name = "repoguardian-rhd"
}

# Production resources are intentionally not declared until account, network,
# secret-management, and deployment targets are selected.
output "deployment_status" {
  value = "skeleton_ready_not_provisioned"
}
