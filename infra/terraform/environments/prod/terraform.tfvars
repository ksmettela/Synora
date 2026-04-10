region = "us-east-1"
cluster_name = "acraas"

vpc_id = "vpc-prod-xxxxxxxx"
subnet_ids = [
  "subnet-prod-xxxxxxxx",
  "subnet-prod-yyyyyyyy",
  "subnet-prod-zzzzzzzz"
]

allowed_cidr_blocks = [
  "10.0.0.0/8"
]

rds_master_username = "postgres"
rds_master_password = "change-me-to-secure-production-password"

sns_topic_arns = [
  "arn:aws:sns:us-east-1:123456789012:acraas-alerts"
]

tags = {
  Environment = "prod"
  Project     = "Synora"
  ManagedBy   = "Terraform"
  Owner       = "platform-team"
  CostCenter  = "engineering"
}
