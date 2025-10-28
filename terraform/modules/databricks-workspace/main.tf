terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  skip_provider_registration = true
}

# Generate random suffix for unique naming
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Resource Group
resource "azurerm_resource_group" "databricks" {
  name     = "rg-databricks-${var.environment}-${random_string.suffix.result}"
  location = var.location
  tags     = var.tags
}

# Databricks Workspace
resource "azurerm_databricks_workspace" "main" {
  name                        = "databricks-${var.environment}-${random_string.suffix.result}"
  resource_group_name         = azurerm_resource_group.databricks.name
  location                    = azurerm_resource_group.databricks.location
  sku                         = var.databricks_sku
  managed_resource_group_name = "databricks-managed-${var.environment}-${random_string.suffix.result}"
  tags                        = var.tags
}
