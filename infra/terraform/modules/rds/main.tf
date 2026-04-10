resource "aws_db_subnet_group" "acraas" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "${var.identifier}-subnet-group"
  })
}

resource "aws_security_group" "rds" {
  name        = "${var.identifier}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.client_security_group_ids
    description     = "PostgreSQL port from application security groups"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.tags, {
    Name = "${var.identifier}-rds-sg"
  })
}

resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "${var.identifier}-rds-key"
  })
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${var.identifier}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

resource "aws_db_parameter_group" "acraas" {
  name   = "${var.identifier}-params"
  family = "postgres16"

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "max_connections"
    value = "500"
  }

  tags = merge(var.tags, {
    Name = "${var.identifier}-params"
  })
}

resource "aws_rds_cluster_parameter_group" "acraas" {
  name   = "${var.identifier}-cluster-params"
  family = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = merge(var.tags, {
    Name = "${var.identifier}-cluster-params"
  })
}

resource "aws_db_instance" "primary" {
  identifier            = var.identifier
  db_name              = var.database_name
  username             = var.master_username
  password             = var.master_password
  instance_class       = var.instance_class
  allocated_storage    = var.allocated_storage
  storage_encrypted    = true
  storage_type         = "gp3"
  kms_key_id          = aws_kms_key.rds.arn

  engine               = "postgres"
  engine_version       = var.engine_version
  family               = "postgres16"
  parameter_group_name = aws_db_parameter_group.acraas.name

  db_subnet_group_name   = aws_db_subnet_group.acraas.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az               = true
  publicly_accessible    = false

  backup_retention_period = var.backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"
  copy_tags_to_snapshot   = true

  enabled_cloudwatch_logs_exports = ["postgresql"]

  enable_iam_database_authentication = true
  deletion_protection              = var.deletion_protection
  skip_final_snapshot              = var.skip_final_snapshot
  final_snapshot_identifier        = var.skip_final_snapshot ? null : "${var.identifier}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = merge(var.tags, {
    Name = var.identifier
  })

  depends_on = [
    aws_db_subnet_group.acraas,
    aws_security_group.rds,
    aws_kms_key.rds,
  ]
}

resource "aws_db_instance" "read_replica" {
  identifier          = "${var.identifier}-read-replica"
  replicate_source_db = aws_db_instance.primary.identifier
  instance_class      = var.read_replica_instance_class
  storage_encrypted   = true
  kms_key_id         = aws_kms_key.rds.arn
  publicly_accessible = false
  skip_final_snapshot = true

  multi_az = false

  tags = merge(var.tags, {
    Name = "${var.identifier}-read-replica"
  })
}

resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name          = "${var.identifier}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS instance CPU utilization is too high"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.primary.id
  }
}

resource "aws_cloudwatch_metric_alarm" "database_connections" {
  alarm_name          = "${var.identifier}-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 400
  alarm_description   = "RDS instance has too many connections"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.primary.id
  }
}

resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name          = "${var.identifier}-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 5368709120
  alarm_description   = "RDS instance has low free storage space (less than 5GB)"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.primary.id
  }
}
