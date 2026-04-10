variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "cluster_name" {
  type        = string
  description = "Base name for the cluster"
  default     = "acraas"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for all resources"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for resource deployment"
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  description = "CIDR blocks allowed for cluster access"
  default     = ["10.0.0.0/8"]
}

variable "rds_master_username" {
  type        = string
  description = "RDS master username"
  default     = "postgres"
}

variable "rds_master_password" {
  type        = string
  description = "RDS master password (minimum 8 characters)"
  sensitive   = true
}

variable "sns_topic_arns" {
  type        = list(string)
  description = "SNS topic ARNs for alarm notifications"
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to all resources"
  default = {
    Environment = "prod"
    Project     = "Synora"
    ManagedBy   = "Terraform"
  }
}
