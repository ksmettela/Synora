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
    bucket         = "acraas-terraform-state-dev"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "acraas-terraform-locks-dev"
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Environment = "dev"
      Project     = "ACRaaS"
      ManagedBy   = "Terraform"
    }
  }
}

module "eks" {
  source = "../../modules/eks"

  cluster_name       = "${var.cluster_name}-dev"
  kubernetes_version = "1.29"
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  allowed_cidr_blocks = var.allowed_cidr_blocks

  on_demand_desired_size = 3
  on_demand_min_size     = 3
  on_demand_max_size     = 10

  spot_desired_size = 2
  spot_min_size     = 0
  spot_max_size     = 10

  tags = var.tags
}

module "msk" {
  source = "../../modules/msk"

  cluster_name             = "${var.cluster_name}-dev"
  vpc_id                   = var.vpc_id
  subnet_ids               = var.subnet_ids
  kafka_version            = "3.5.1"
  number_of_broker_nodes   = 3
  broker_instance_type     = "kafka.m5.xlarge"
  storage_volume_size      = 1000
  configuration_name       = "${var.cluster_name}-dev-config"
  log_retention_hours      = 168
  default_partitions       = 6
  replication_factor       = 3
  min_insync_replicas      = 2
  client_security_group_ids = [module.eks.eks_cluster_sg_id]
  allowed_cidr_blocks      = var.allowed_cidr_blocks
  client_principals        = [module.eks.node_role_arn]
  log_retention_days       = 7

  tags = var.tags
}

module "s3" {
  source = "../../modules/s3"

  environment = "dev"
  tags        = var.tags
}

module "elasticache" {
  source = "../../modules/elasticache"

  replication_group_id      = "${var.cluster_name}-dev-redis"
  description               = "ACRaaS Redis cluster for dev"
  vpc_id                    = var.vpc_id
  subnet_ids                = var.subnet_ids
  node_type                 = "cache.t4g.medium"
  num_node_groups           = 2
  replicas_per_node_group   = 1
  engine_version            = "7.1"
  client_security_group_ids = [module.eks.eks_cluster_sg_id]
  log_retention_days        = 7

  tags = var.tags
}

module "rds" {
  source = "../../modules/rds"

  identifier                 = "${var.cluster_name}-dev-postgres"
  database_name              = "acraas_dev"
  master_username            = "postgres"
  master_password            = var.rds_master_password
  vpc_id                     = var.vpc_id
  subnet_ids                 = var.subnet_ids
  instance_class             = "db.t4g.medium"
  read_replica_instance_class = "db.t4g.medium"
  engine_version             = "16.1"
  allocated_storage          = 50
  backup_retention_days      = 7
  deletion_protection        = false
  skip_final_snapshot        = true
  client_security_group_ids  = [module.eks.eks_cluster_sg_id]
  alarm_actions              = []

  tags = var.tags
}

output "eks_cluster_name" {
  value       = module.eks.cluster_name
  description = "EKS cluster name"
}

output "msk_bootstrap_brokers" {
  value       = module.msk.bootstrap_brokers_tls
  description = "MSK bootstrap brokers (TLS)"
}

output "elasticache_endpoint" {
  value       = module.elasticache.configuration_endpoint_address
  description = "ElastiCache cluster endpoint"
}

output "rds_endpoint" {
  value       = module.rds.database_endpoint
  description = "RDS database endpoint"
}

output "s3_viewership_bucket" {
  value       = module.s3.viewership_bucket_name
  description = "S3 bucket for viewership data lake"
}
