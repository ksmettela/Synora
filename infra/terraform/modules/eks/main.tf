resource "aws_eks_cluster" "acraas" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = false
    security_group_ids      = [aws_security_group.eks_cluster.id]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_service_policy,
  ]

  tags = var.tags
}

resource "aws_eks_node_group" "on_demand" {
  cluster_name    = aws_eks_cluster.acraas.name
  node_group_name = "${var.cluster_name}-on-demand"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = var.subnet_ids
  version         = var.kubernetes_version

  scaling_config {
    desired_size = var.on_demand_desired_size
    max_size     = var.on_demand_max_size
    min_size     = var.on_demand_min_size
  }

  instance_types = ["t3.large"]

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-on-demand"
  })

  depends_on = [
    aws_iam_role_policy_attachment.eks_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_registry_policy,
  ]
}

resource "aws_eks_node_group" "spot" {
  cluster_name    = aws_eks_cluster.acraas.name
  node_group_name = "${var.cluster_name}-spot"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = var.subnet_ids
  version         = var.kubernetes_version

  scaling_config {
    desired_size = var.spot_desired_size
    max_size     = var.spot_max_size
    min_size     = var.spot_min_size
  }

  instance_types = ["m5.xlarge"]
  capacity_type  = "SPOT"

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-spot"
  })

  depends_on = [
    aws_iam_role_policy_attachment.eks_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_registry_policy,
  ]
}

resource "aws_iam_role" "eks_cluster" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role_policy_attachment" "eks_service_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role" "eks_node" {
  name = "${var.cluster_name}-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "eks_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_registry_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node.name
}

resource "aws_security_group" "eks_cluster" {
  name        = "${var.cluster_name}-cluster-sg"
  description = "Security group for EKS cluster"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Allow HTTPS from allowed CIDR blocks"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-cluster-sg"
  })
}

resource "aws_security_group_rule" "eks_node_to_cluster" {
  type                     = "ingress"
  from_port                = 1025
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.eks_cluster.id
  security_group_id        = aws_security_group.eks_cluster.id
  description              = "Allow node to cluster communication"
}

data "tls_certificate" "cluster" {
  url = aws_eks_cluster.acraas.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "cluster" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.cluster.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.acraas.identity[0].oidc[0].issuer

  tags = var.tags
}

resource "aws_iam_role" "load_balancer_controller" {
  name = "${var.cluster_name}-load-balancer-controller"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.cluster.arn
        }
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.cluster.url, "https://", "")}:sub" = "system:serviceaccount:kube-system:aws-load-balancer-controller"
          }
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "load_balancer_controller" {
  name   = "${var.cluster_name}-load-balancer-controller"
  role   = aws_iam_role.load_balancer_controller.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elbv2:CreateLoadBalancer",
          "elbv2:CreateTargetGroup",
          "elbv2:DescribeLoadBalancers",
          "elbv2:DescribeTargetGroups",
          "elbv2:DescribeLoadBalancerAttributes",
          "elbv2:DescribeTargetGroupAttributes",
          "elbv2:ModifyLoadBalancerAttributes",
          "elbv2:ModifyTargetGroupAttributes",
          "elbv2:DeleteLoadBalancer",
          "elbv2:DeleteTargetGroup",
          "elbv2:CreateListener",
          "elbv2:DeleteListener",
          "elbv2:ModifyListener",
          "elbv2:DescribeListeners",
          "elbv2:DescribeListenerCertificates",
          "elbv2:AddListenerCertificates",
          "elbv2:RemoveListenerCertificates",
          "elbv2:ModifyRule",
          "elbv2:DescribeRules",
          "elbv2:CreateRule",
          "elbv2:DeleteRule",
          "elbv2:RegisterTargets",
          "elbv2:DeregisterTargets"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus",
          "ec2:DescribeTags",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeInstanceAttribute",
          "ec2:ModifyInstanceAttribute",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeAddresses",
          "ec2:AssociateAddress"
        ]
        Resource = "*"
      }
    ]
  })
}
