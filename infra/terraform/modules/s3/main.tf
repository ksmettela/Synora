resource "aws_s3_bucket" "viewership_data_lake" {
  bucket = "acraas-viewership-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.tags, {
    Name = "acraas-viewership-${var.environment}"
  })
}

resource "aws_s3_bucket_versioning" "viewership_data_lake" {
  bucket = aws_s3_bucket.viewership_data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "viewership_data_lake" {
  bucket = aws_s3_bucket.viewership_data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "viewership_data_lake" {
  bucket = aws_s3_bucket.viewership_data_lake.id

  rule {
    id     = "intelligent-tiering"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "INTELLIGENT_TIERING"
    }

    noncurrent_version_expiration {
      noncurrent_days = 730
    }
  }
}

resource "aws_s3_bucket_public_access_block" "viewership_data_lake" {
  bucket = aws_s3_bucket.viewership_data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_logging" "viewership_data_lake" {
  bucket = aws_s3_bucket.viewership_data_lake.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "viewership/"
}

resource "aws_s3_bucket" "archives" {
  bucket = "acraas-archives-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.tags, {
    Name = "acraas-archives-${var.environment}"
  })
}

resource "aws_s3_bucket_versioning" "archives" {
  bucket = aws_s3_bucket.archives.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "archives" {
  bucket = aws_s3_bucket.archives.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "archives" {
  bucket = aws_s3_bucket.archives.id

  rule {
    id     = "archive-to-deep-archive"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "DEEP_ARCHIVE"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "archives" {
  bucket = aws_s3_bucket.archives.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_logging" "archives" {
  bucket = aws_s3_bucket.archives.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "archives/"
}

resource "aws_s3_bucket" "audit_log" {
  bucket = "acraas-audit-log-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.tags, {
    Name = "acraas-audit-log-${var.environment}"
  })
}

resource "aws_s3_bucket_versioning" "audit_log" {
  bucket = aws_s3_bucket.audit_log.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_log" {
  bucket = aws_s3_bucket.audit_log.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audit_log" {
  bucket = aws_s3_bucket.audit_log.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_logging" "audit_log" {
  bucket = aws_s3_bucket.audit_log.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "audit/"
}

resource "aws_s3_bucket_policy" "audit_log_immutable" {
  bucket = aws_s3_bucket.audit_log.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyObjectDeletion"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion"
        ]
        Resource = "${aws_s3_bucket.audit_log.arn}/*"
      },
      {
        Sid    = "DenyBucketDeletion"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:DeleteBucket"
        ]
        Resource = aws_s3_bucket.audit_log.arn
      }
    ]
  })
}

resource "aws_s3_bucket" "sdk_distribution" {
  bucket = "acraas-sdk-distribution-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.tags, {
    Name = "acraas-sdk-distribution-${var.environment}"
  })
}

resource "aws_s3_bucket_versioning" "sdk_distribution" {
  bucket = aws_s3_bucket.sdk_distribution.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "sdk_distribution" {
  bucket = aws_s3_bucket.sdk_distribution.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "sdk_distribution" {
  bucket = aws_s3_bucket.sdk_distribution.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "sdk_distribution_public_read" {
  bucket = aws_s3_bucket.sdk_distribution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "PublicRead"
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action = "s3:GetObject"
        Resource = "${aws_s3_bucket.sdk_distribution.arn}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_logging" "sdk_distribution" {
  bucket = aws_s3_bucket.sdk_distribution.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "sdk/"
}

resource "aws_s3_bucket" "access_logs" {
  bucket = "acraas-access-logs-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.tags, {
    Name = "acraas-access-logs-${var.environment}"
  })
}

resource "aws_s3_bucket_versioning" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

resource "aws_kms_key" "s3" {
  description             = "KMS key for Synora S3 buckets"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "acraas-s3-key"
  })
}

resource "aws_kms_alias" "s3" {
  name          = "alias/acraas-s3-${var.environment}"
  target_key_id = aws_kms_key.s3.key_id
}

data "aws_caller_identity" "current" {}
