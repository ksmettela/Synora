output "viewership_bucket_name" {
  value       = aws_s3_bucket.viewership_data_lake.id
  description = "Name of the viewership data lake bucket"
}

output "viewership_bucket_arn" {
  value       = aws_s3_bucket.viewership_data_lake.arn
  description = "ARN of the viewership data lake bucket"
}

output "archives_bucket_name" {
  value       = aws_s3_bucket.archives.id
  description = "Name of the archives bucket"
}

output "archives_bucket_arn" {
  value       = aws_s3_bucket.archives.arn
  description = "ARN of the archives bucket"
}

output "audit_log_bucket_name" {
  value       = aws_s3_bucket.audit_log.id
  description = "Name of the audit log bucket"
}

output "audit_log_bucket_arn" {
  value       = aws_s3_bucket.audit_log.arn
  description = "ARN of the audit log bucket"
}

output "sdk_distribution_bucket_name" {
  value       = aws_s3_bucket.sdk_distribution.id
  description = "Name of the SDK distribution bucket"
}

output "sdk_distribution_bucket_arn" {
  value       = aws_s3_bucket.sdk_distribution.arn
  description = "ARN of the SDK distribution bucket"
}

output "access_logs_bucket_name" {
  value       = aws_s3_bucket.access_logs.id
  description = "Name of the access logs bucket"
}

output "kms_key_id" {
  value       = aws_kms_key.s3.id
  description = "KMS key ID for S3 encryption"
  sensitive   = true
}

output "kms_key_arn" {
  value       = aws_kms_key.s3.arn
  description = "KMS key ARN for S3 encryption"
}
