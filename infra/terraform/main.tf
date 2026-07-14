# eラーニング統合プラットフォーム — インフラ骨格
# 目標構成:
#   Internet → Route53 → CloudFront → (S3 | ALB → ECS Fargate)
#   ECS: 受講API / 添削API / 管理API / バッチ
#   Cognito → Aurora PostgreSQL(RDS)
#   CloudWatch / WAF / SES / SQS
#
# 対象モジュール（現状骨格）: VPC / RDS / Cognito / ECS+CloudFront

terraform {
  required_version = ">= 1.5.0"
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

variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "project_name" {
  type    = string
  default = "elearning"
}

variable "environment" {
  type    = string
  default = "dev"
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# --- VPC (骨格) ---
module "vpc" {
  source = "./modules/vpc"
  name   = local.name_prefix
  tags   = local.tags
}

# --- RDS PostgreSQL ---
module "rds" {
  source         = "./modules/rds"
  name           = local.name_prefix
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnet_ids
  tags           = local.tags
}

# --- Cognito User Pool ---
module "cognito" {
  source = "./modules/cognito"
  name   = local.name_prefix
  tags   = local.tags
}

# --- ECS (API) + ALB + CloudFront (Web) ---
module "ecs" {
  source             = "./modules/ecs"
  name               = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids
  tags               = local.tags
}

output "cognito_user_pool_id" {
  value = module.cognito.user_pool_id
}

output "cognito_client_id" {
  value = module.cognito.client_id
}

output "rds_endpoint" {
  value     = module.rds.endpoint
  sensitive = true
}
