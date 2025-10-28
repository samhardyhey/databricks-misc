variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "databricks_sku" {
  description = "Databricks workspace SKU (standard, premium)"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium"], var.databricks_sku)
    error_message = "Databricks SKU must be either 'standard' or 'premium'."
  }
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
