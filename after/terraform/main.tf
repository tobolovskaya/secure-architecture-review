# Hardened version of before/terraform/main.tf: explicit VPC, descriptions, and only listed networks on 443.
# For a public API, put a load balancer with WAF in front and allow only its subnets here.
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_security_group" "user_api" {
  # checkov:skip=CKV2_AWS_5:The group is attached by the load balancer module, which is outside this review
  name        = "user-api-sg"
  description = "HTTPS to the user API from allowed networks only"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS from allowed networks"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  egress {
    description = "HTTPS out, for example to the secrets store"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
