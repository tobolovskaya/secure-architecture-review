variable "aws_region" {
  description = "AWS region for the service"
  type        = string
  default     = "eu-north-1"
}

variable "vpc_id" {
  description = "VPC the security group belongs to"
  type        = string
}

variable "allowed_cidrs" {
  description = "Networks allowed to reach the API on 443, for example the load balancer subnets or a VPN range"
  type        = list(string)

  validation {
    condition     = length(var.allowed_cidrs) > 0 && !contains(var.allowed_cidrs, "0.0.0.0/0")
    error_message = "allowed_cidrs must list specific networks, not 0.0.0.0/0."
  }
}
