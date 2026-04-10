resource "aws_elasticache_subnet_group" "acraas" {
  name       = "${var.replication_group_id}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "${var.replication_group_id}-subnet-group"
  })
}

resource "aws_elasticache_parameter_group" "acraas" {
  family = "redis7.1"
  name   = "${var.replication_group_id}-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }

  tags = merge(var.tags, {
    Name = "${var.replication_group_id}-params"
  })
}

resource "aws_elasticache_replication_group" "acraas" {
  replication_group_id       = var.replication_group_id
  description                = var.description
  node_type                  = var.node_type
  num_node_groups            = var.num_node_groups
  replicas_per_node_group    = var.replicas_per_node_group
  engine                     = "redis"
  engine_version             = var.engine_version
  port                       = 6379
  parameter_group_name       = aws_elasticache_parameter_group.acraas.name
  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.auth_token
  subnet_group_name          = aws_elasticache_subnet_group.acraas.name
  security_group_ids         = [aws_security_group.elasticache.id]
  automatic_failover_enabled = true
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.engine_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  tags = merge(var.tags, {
    Name = var.replication_group_id
  })

  depends_on = [
    aws_elasticache_parameter_group.acraas,
    aws_elasticache_subnet_group.acraas,
    aws_security_group.elasticache,
  ]
}

resource "aws_security_group" "elasticache" {
  name        = "${var.replication_group_id}-sg"
  description = "Security group for ElastiCache Redis cluster"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.client_security_group_ids
    description     = "Redis port from client security groups"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.tags, {
    Name = "${var.replication_group_id}-sg"
  })
}

resource "aws_cloudwatch_log_group" "slow_log" {
  name              = "/aws/elasticache/${var.replication_group_id}/slow-log"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${var.replication_group_id}-slow-log"
  })
}

resource "aws_cloudwatch_log_group" "engine_log" {
  name              = "/aws/elasticache/${var.replication_group_id}/engine-log"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${var.replication_group_id}-engine-log"
  })
}
