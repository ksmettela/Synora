variable "cluster_name" {
  type        = string
  description = "Name of the EKS cluster"
}

variable "kubernetes_version" {
  type        = string
  description = "Kubernetes version for the cluster"
  default     = "1.29"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where the cluster will be deployed"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for the cluster"
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  description = "CIDR blocks allowed to access the cluster API"
  default     = ["0.0.0.0/0"]
}

variable "on_demand_desired_size" {
  type        = number
  description = "Desired number of on-demand nodes"
  default     = 3
}

variable "on_demand_min_size" {
  type        = number
  description = "Minimum number of on-demand nodes"
  default     = 3
}

variable "on_demand_max_size" {
  type        = number
  description = "Maximum number of on-demand nodes"
  default     = 10
}

variable "spot_desired_size" {
  type        = number
  description = "Desired number of spot nodes"
  default     = 5
}

variable "spot_min_size" {
  type        = number
  description = "Minimum number of spot nodes"
  default     = 0
}

variable "spot_max_size" {
  type        = number
  description = "Maximum number of spot nodes"
  default     = 20
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default = {
    Project = "ACRaaS"
    Component = "Infrastructure"
  }
}
