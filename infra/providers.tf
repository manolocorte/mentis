terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }

  # Remote state. Configured via `-backend-config` flags in CI (see
  # .github/workflows/deploy.yml) and for local use:
  #   terraform init \
  #     -backend-config="bucket=<your-state-bucket>" \
  #     -backend-config="key=mentis/prod/terraform.tfstate" \
  #     -backend-config="region=us-east-1" \
  #     -backend-config="use_lockfile=true"
  # `use_lockfile` uses S3-native locking (Terraform >= 1.10) — no DynamoDB table needed.
  backend "s3" {
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
