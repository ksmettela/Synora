region = "us-east-1"
cluster_name = "acraas"

vpc_id = "vpc-xxxxxxxx"
subnet_ids = [
  "subnet-xxxxxxxx",
  "subnet-yyyyyyyy",
  "subnet-zzzzzzzz"
]

allowed_cidr_blocks = [
  "10.0.0.0/8",
  "172.16.0.0/12"
]

rds_master_password = "changeme_to_secure_password"

tags = {
  Environment = "dev"
  Project     = "Synora"
  ManagedBy   = "Terraform"
  Owner       = "platform-team"
}
