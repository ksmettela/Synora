output "primary_endpoint_address" {
  value       = aws_elasticache_replication_group.acraas.primary_endpoint_address
  description = "Address of the primary endpoint"
}

output "primary_endpoint_address_with_port" {
  value       = aws_elasticache_replication_group.acraas.primary_endpoint_address
  description = "Primary endpoint address"
}

output "configuration_endpoint_address" {
  value       = aws_elasticache_replication_group.acraas.configuration_endpoint_address
  description = "Configuration endpoint address for cluster mode enabled"
}

output "replication_group_id" {
  value       = aws_elasticache_replication_group.acraas.id
  description = "ID of the replication group"
}

output "replication_group_arn" {
  value       = aws_elasticache_replication_group.acraas.arn
  description = "ARN of the replication group"
}

output "member_clusters" {
  value       = aws_elasticache_replication_group.acraas.member_clusters
  description = "List of member cluster IDs"
}

output "security_group_id" {
  value       = aws_security_group.elasticache.id
  description = "Security group ID for the ElastiCache cluster"
}

output "port" {
  value       = 6379
  description = "Redis port"
}
