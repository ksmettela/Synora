variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default = {
    Project   = "ACRaaS"
    Component = "Storage"
  }
}
