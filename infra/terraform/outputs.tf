output "eks_cluster_id" {
  value       = try(aws_eks_cluster.main.id, "")
  description = "EKS cluster ID"
}

output "msk_bootstrap_brokers" {
  value       = try(aws_msk_cluster.acraas.bootstrap_brokers, "")
  description = "MSK bootstrap brokers"
}

output "s3_data_lake_bucket" {
  value       = try(aws_s3_bucket.data_lake.id, "")
  description = "S3 data lake bucket"
}
