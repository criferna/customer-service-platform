# =============================================================================
# Terraform Configuration
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    bucket         = "lab-ms-terraform-state"
    key            = "customer-service-platform/terraform.tfstate"
    region         = "us-east-2"
    dynamodb_table = "lab-ms-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "customer-service-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
