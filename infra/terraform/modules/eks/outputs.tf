output "cluster_name" {
  value       = aws_eks_cluster.acraas.name
  description = "Name of the EKS cluster"
}

output "cluster_endpoint" {
  value       = aws_eks_cluster.acraas.endpoint
  description = "Endpoint for your Kubernetes API server"
}

output "cluster_ca_certificate" {
  value       = base64decode(aws_eks_cluster.acraas.certificate_authority[0].data)
  description = "Base64 encoded certificate data required to communicate with the cluster"
  sensitive   = true
}

output "cluster_iam_role_arn" {
  value       = aws_iam_role.eks_cluster.arn
  description = "IAM role ARN of the EKS cluster"
}

output "node_role_arn" {
  value       = aws_iam_role.eks_node.arn
  description = "IAM role ARN for the EKS nodes"
}

output "oidc_provider_arn" {
  value       = aws_iam_openid_connect_provider.cluster.arn
  description = "ARN of the OIDC provider"
}

output "load_balancer_controller_role_arn" {
  value       = aws_iam_role.load_balancer_controller.arn
  description = "ARN of the load balancer controller IAM role"
}

output "eks_cluster_sg_id" {
  value       = aws_security_group.eks_cluster.id
  description = "Security group ID for the EKS cluster"
}
