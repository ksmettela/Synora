variable "replication_group_id" {
  type        = string
  description = "Name of the replication group"
  default     = "acraas-redis"
}

variable "description" {
  type        = string
  description = "Description of the replication group"
  default     = "Synora Redis cluster for caching and real-time data"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the cluster"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for the cluster"
}

variable "node_type" {
  type        = string
  description = "Node type for the cluster"
  default     = "cache.r7g.xlarge"
}

variable "num_node_groups" {
  type        = number
  description = "Number of shards (node groups)"
  default     = 3
}

variable "replicas_per_node_group" {
  type        = number
  description = "Number of replica nodes per shard"
  default     = 1
}

variable "engine_version" {
  type        = string
  description = "Redis engine version"
  default     = "7.1"
}

variable "auth_token" {
  type        = string
  description = "Auth token for Redis (6+ character alphanumeric string)"
  default     = ""
  sensitive   = true
}

variable "client_security_group_ids" {
  type        = list(string)
  description = "Security group IDs of clients allowed to connect"
  default     = []
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days"
  default     = 7
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default = {
    Project   = "Synora"
    Component = "Cache"
  }
}
