terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "acraas-terraform-state-prod"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "acraas-terraform-locks-prod"
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Environment = "prod"
      Project     = "Synora"
      ManagedBy   = "Terraform"
    }
  }
}

module "eks" {
  source = "../../modules/eks"

  cluster_name       = "${var.cluster_name}-prod"
  kubernetes_version = "1.29"
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  allowed_cidr_blocks = var.allowed_cidr_blocks

  on_demand_desired_size = 5
  on_demand_min_size     = 5
  on_demand_max_size     = 20

  spot_desired_size = 10
  spot_min_size     = 5
  spot_max_size     = 50

  tags = var.tags
}

module "msk" {
  source = "../../modules/msk"

  cluster_name             = "${var.cluster_name}-prod"
  vpc_id                   = var.vpc_id
  subnet_ids               = var.subnet_ids
  kafka_version            = "3.5.1"
  number_of_broker_nodes   = 5
  broker_instance_type     = "kafka.m5.2xlarge"
  storage_volume_size      = 5000
  configuration_name       = "${var.cluster_name}-prod-config"
  log_retention_hours      = 720
  default_partitions       = 12
  replication_factor       = 3
  min_insync_replicas      = 2
  client_security_group_ids = [module.eks.eks_cluster_sg_id]
  allowed_cidr_blocks      = var.allowed_cidr_blocks
  client_principals        = [module.eks.node_role_arn]
  log_retention_days       = 30

  tags = var.tags
}

module "s3" {
  source = "../../modules/s3"

  environment = "prod"
  tags        = var.tags
}

module "elasticache" {
  source = "../../modules/elasticache"

  replication_group_id      = "${var.cluster_name}-prod-redis"
  description               = "Synora Redis cluster for production"
  vpc_id                    = var.vpc_id
  subnet_ids                = var.subnet_ids
  node_type                 = "cache.r7g.xlarge"
  num_node_groups           = 3
  replicas_per_node_group   = 2
  engine_version            = "7.1"
  client_security_group_ids = [module.eks.eks_cluster_sg_id]
  log_retention_days        = 30

  tags = var.tags
}

module "rds" {
  source = "../../modules/rds"

  identifier                 = "${var.cluster_name}-prod-postgres"
  database_name              = "acraas"
  master_username            = var.rds_master_username
  master_password            = var.rds_master_password
  vpc_id                     = var.vpc_id
  subnet_ids                 = var.subnet_ids
  instance_class             = "db.r7g.xlarge"
  read_replica_instance_class = "db.r7g.large"
  engine_version             = "16.1"
  allocated_storage          = 500
  backup_retention_days      = 30
  deletion_protection        = true
  skip_final_snapshot        = false
  client_security_group_ids  = [module.eks.eks_cluster_sg_id]
  alarm_actions              = var.sns_topic_arns

  tags = var.tags
}

output "eks_cluster_name" {
  value       = module.eks.cluster_name
  description = "EKS cluster name"
}

output "eks_cluster_endpoint" {
  value       = module.eks.cluster_endpoint
  description = "EKS cluster endpoint"
}

output "msk_bootstrap_brokers" {
  value       = module.msk.bootstrap_brokers_tls
  description = "MSK bootstrap brokers (TLS)"
}

output "msk_cluster_arn" {
  value       = module.msk.cluster_arn
  description = "MSK cluster ARN"
}

output "elasticache_endpoint" {
  value       = module.elasticache.configuration_endpoint_address
  description = "ElastiCache cluster endpoint"
}

output "elasticache_primary_endpoint" {
  value       = module.elasticache.primary_endpoint_address
  description = "ElastiCache primary endpoint"
}

output "rds_endpoint" {
  value       = module.rds.database_endpoint
  description = "RDS database endpoint"
  sensitive   = true
}

output "rds_read_replica_endpoint" {
  value       = module.rds.read_replica_endpoint
  description = "RDS read replica endpoint"
  sensitive   = true
}

output "s3_viewership_bucket" {
  value       = module.s3.viewership_bucket_name
  description = "S3 bucket for viewership data lake"
}

output "s3_archives_bucket" {
  value       = module.s3.archives_bucket_name
  description = "S3 bucket for archives"
}

output "s3_audit_log_bucket" {
  value       = module.s3.audit_log_bucket_name
  description = "S3 bucket for audit logs"
}
