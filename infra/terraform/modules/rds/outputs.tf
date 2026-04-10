output "database_endpoint" {
  value       = aws_db_instance.primary.endpoint
  description = "Database endpoint (address:port)"
}

output "database_host" {
  value       = aws_db_instance.primary.address
  description = "Database host address"
}

output "database_port" {
  value       = aws_db_instance.primary.port
  description = "Database port"
}

output "database_name" {
  value       = aws_db_instance.primary.db_name
  description = "Name of the database"
}

output "database_username" {
  value       = aws_db_instance.primary.username
  description = "Master username"
  sensitive   = true
}

output "database_resource_id" {
  value       = aws_db_instance.primary.resource_id
  description = "Database resource ID"
}

output "database_arn" {
  value       = aws_db_instance.primary.arn
  description = "Database ARN"
}

output "read_replica_endpoint" {
  value       = aws_db_instance.read_replica.endpoint
  description = "Read replica endpoint"
}

output "read_replica_host" {
  value       = aws_db_instance.read_replica.address
  description = "Read replica host address"
}

output "security_group_id" {
  value       = aws_security_group.rds.id
  description = "Security group ID for the database"
}

output "kms_key_id" {
  value       = aws_kms_key.rds.id
  description = "KMS key ID for database encryption"
  sensitive   = true
}
