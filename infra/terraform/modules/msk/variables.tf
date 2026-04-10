variable "cluster_name" {
  type        = string
  description = "Name of the MSK cluster"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the cluster"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for broker deployment"
}

variable "kafka_version" {
  type        = string
  description = "Kafka version"
  default     = "3.5.1"
}

variable "number_of_broker_nodes" {
  type        = number
  description = "Number of broker nodes"
  default     = 3
}

variable "broker_instance_type" {
  type        = string
  description = "Instance type for Kafka brokers"
  default     = "kafka.m5.xlarge"
}

variable "storage_volume_size" {
  type        = number
  description = "EBS volume size for brokers in GB"
  default     = 1000
}

variable "configuration_name" {
  type        = string
  description = "Name of the MSK configuration"
  default     = "acraas-config"
}

variable "log_retention_hours" {
  type        = number
  description = "Log retention in hours"
  default     = 168
}

variable "default_partitions" {
  type        = number
  description = "Default number of partitions"
  default     = 6
}

variable "replication_factor" {
  type        = number
  description = "Default replication factor"
  default     = 3
}

variable "min_insync_replicas" {
  type        = number
  description = "Minimum in-sync replicas"
  default     = 2
}

variable "client_security_group_ids" {
  type        = list(string)
  description = "Security group IDs of clients allowed to connect"
  default     = []
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  description = "CIDR blocks allowed for Zookeeper access"
  default     = ["0.0.0.0/0"]
}

variable "client_principals" {
  type        = list(string)
  description = "ARNs of principals allowed to assume the MSK client role"
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
    Component = "Messaging"
  }
}
