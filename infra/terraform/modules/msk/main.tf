resource "aws_msk_cluster" "acraas" {
  cluster_name           = var.cluster_name
  kafka_version          = var.kafka_version
  number_of_broker_nodes = var.number_of_broker_nodes

  broker_node_group_info {
    instance_type   = var.broker_instance_type
    client_subnets  = var.subnet_ids
    security_groups = [aws_security_group.msk.id]

    storage_info {
      ebs_storage_info {
        volume_size = var.storage_volume_size
      }
    }

    connectivity_info {
      public_access {
        type = "DISABLED"
      }
    }
  }

  cluster_configuration {
    instance_family         = "kafka"
    kafka_version           = var.kafka_version
    number_of_broker_nodes  = var.number_of_broker_nodes
    configuration_info {
      arn      = aws_msk_configuration.acraas.arn
      revision = aws_msk_configuration.acraas.latest_revision
    }
  }

  encryption_info {
    encryption_at_rest {
      data_volume_kms_key_id = aws_kms_key.msk.arn
    }
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  client_authentication {
    sasl {
      iam = true
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk.name
      }
    }
  }

  tags = var.tags

  depends_on = [
    aws_msk_configuration.acraas,
    aws_kms_key.msk,
  ]
}

resource "aws_msk_configuration" "acraas" {
  name              = var.configuration_name
  kafka_versions    = [var.kafka_version]
  server_properties = <<PROPERTIES
log.retention.hours=${var.log_retention_hours}
num.partitions=${var.default_partitions}
default.replication.factor=${var.replication_factor}
min.insync.replicas=${var.min_insync_replicas}
auto.create.topics.enable=false
log.cleanup.policy=delete
compression.type=snappy
PROPERTIES
}

resource "aws_security_group" "msk" {
  name        = "${var.cluster_name}-msk-sg"
  description = "Security group for MSK cluster"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    security_groups = var.client_security_group_ids
    description     = "Kafka broker port (PLAINTEXT)"
  }

  ingress {
    from_port       = 9094
    to_port         = 9094
    protocol        = "tcp"
    security_groups = var.client_security_group_ids
    description     = "Kafka broker port (TLS)"
  }

  ingress {
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Zookeeper port"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-msk-sg"
  })
}

resource "aws_kms_key" "msk" {
  description             = "KMS key for MSK cluster ${var.cluster_name}"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-msk-key"
  })
}

resource "aws_kms_alias" "msk" {
  name          = "alias/${var.cluster_name}-msk"
  target_key_id = aws_kms_key.msk.key_id
}

resource "aws_cloudwatch_log_group" "msk" {
  name              = "/aws/msk/${var.cluster_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-msk-logs"
  })
}

resource "aws_iam_role" "msk_client" {
  name = "${var.cluster_name}-msk-client-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = var.client_principals
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "msk_client" {
  name   = "${var.cluster_name}-msk-client-policy"
  role   = aws_iam_role.msk_client.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kafka:GetBootstrapBrokers",
          "kafka:DescribeCluster",
          "kafka-cluster:Connect",
          "kafka-cluster:AlterCluster",
          "kafka-cluster:DescribeCluster",
          "kafka-cluster:*Topic*",
          "kafka-cluster:WriteData",
          "kafka-cluster:ReadData"
        ]
        Resource = aws_msk_cluster.acraas.arn
      }
    ]
  })
