output "bootstrap_brokers" {
  value       = aws_msk_cluster.acraas.bootstrap_brokers
  description = "Kafka bootstrap brokers (plaintext)"
}

output "bootstrap_brokers_tls" {
  value       = aws_msk_cluster.acraas.bootstrap_brokers_tls
  description = "Kafka bootstrap brokers (TLS)"
}

output "zookeeper_connect_string" {
  value       = aws_msk_cluster.acraas.zookeeper_connect_string
  description = "Zookeeper connection string"
}

output "cluster_arn" {
  value       = aws_msk_cluster.acraas.arn
  description = "ARN of the MSK cluster"
}

output "cluster_name" {
  value       = aws_msk_cluster.acraas.cluster_name
  description = "Name of the MSK cluster"
}

output "msk_security_group_id" {
  value       = aws_security_group.msk.id
  description = "Security group ID for MSK cluster"
}

output "msk_client_role_arn" {
  value       = aws_iam_role.msk_client.arn
  description = "ARN of the MSK client IAM role"
}

output "kms_key_id" {
  value       = aws_kms_key.msk.id
  description = "KMS key ID for MSK encryption"
  sensitive   = true
}
