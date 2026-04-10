variable "identifier" {
  type        = string
  description = "Database instance identifier"
  default     = "acraas-postgres"
}

variable "database_name" {
  type        = string
  description = "Name of the database"
  default     = "acraas"
}

variable "master_username" {
  type        = string
  description = "Master username for the database"
  default     = "postgres"
  sensitive   = true
}

variable "master_password" {
  type        = string
  description = "Master password for the database (minimum 8 characters)"
  sensitive   = true
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the database"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for the database"
}

variable "instance_class" {
  type        = string
  description = "Instance class for the database"
  default     = "db.r7g.large"
}

variable "read_replica_instance_class" {
  type        = string
  description = "Instance class for the read replica"
  default     = "db.r7g.large"
}

variable "engine_version" {
  type        = string
  description = "PostgreSQL engine version"
  default     = "16.1"
}

variable "allocated_storage" {
  type        = number
  description = "Allocated storage in GB"
  default     = 100
}

variable "backup_retention_days" {
  type        = number
  description = "Number of days to retain backups"
  default     = 7
}

variable "deletion_protection" {
  type        = bool
  description = "Enable deletion protection"
  default     = true
}

variable "skip_final_snapshot" {
  type        = bool
  description = "Skip final snapshot before deletion"
  default     = false
}

variable "client_security_group_ids" {
  type        = list(string)
  description = "Security group IDs of clients allowed to connect"
  default     = []
}

variable "alarm_actions" {
  type        = list(string)
  description = "SNS topic ARNs for CloudWatch alarms"
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default = {
    Project   = "Synora"
    Component = "Database"
  }
}
