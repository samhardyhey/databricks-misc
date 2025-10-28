terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.0"
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

provider "azuread" {
  # Uses Azure CLI authentication by default
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

# Get current user info
data "azurerm_client_config" "current" {}

# Create Azure AD group for Databricks access
resource "azuread_group" "databricks_users" {
  display_name     = "databricks-${var.environment}-users"
  description      = "Users with access to Databricks ${var.environment} workspace"
  security_enabled = true
}

# Add yourself to the Azure AD group
resource "azuread_group_member" "admin_user" {
  group_object_id  = azuread_group.databricks_users.object_id
  member_object_id = data.azurerm_client_config.current.object_id
}

# Grant the Azure AD group access to the Databricks workspace
resource "azurerm_role_assignment" "databricks_group_access" {
  scope                = azurerm_databricks_workspace.main.id
  role_definition_name = "Contributor"
  principal_id         = azuread_group.databricks_users.object_id
}

# Also grant direct user access (backup for external users)
resource "azurerm_role_assignment" "databricks_user_access" {
  scope                = azurerm_databricks_workspace.main.id
  role_definition_name = "Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Databricks Provider Configuration
provider "databricks" {
  host = azurerm_databricks_workspace.main.workspace_url
}
