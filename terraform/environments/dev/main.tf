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
# For workspace-level resources
provider "databricks" {
  host = azurerm_databricks_workspace.main.workspace_url
}

# Account-level provider for Unity Catalog resources
# Unity Catalog metastores require account-level authentication
# NOTE: Account portal access requires a work/school Azure AD account
# Personal Microsoft accounts (gmail.com, outlook.com) cannot access the account portal
#
# Options:
# 1. Use a work/school Azure AD account that has access
# 2. Create metastore manually via Databricks workspace UI (see comments below)
# 3. Use Azure AD authentication if your account has proper permissions
provider "databricks" {
  alias = "account"
  host  = "https://accounts.azuredatabricks.net"

  # Try Azure CLI authentication - may work if account has proper Azure AD permissions
  # If this doesn't work, you'll need to create the metastore manually
}

# ============================================================================
# Unity Catalog Configuration
# ============================================================================
# Unity Catalog requires:
# 1. Premium tier (set via databricks_sku = "premium")
# 2. Storage account with hierarchical namespace (Data Lake Storage Gen2)
# 3. Workspace managed identity with Storage Blob Data Contributor role
# 4. Metastore resource

# Storage Account for Unity Catalog Metastore
# Note: Storage account names must be globally unique and 3-24 chars, lowercase alphanumeric
resource "azurerm_storage_account" "unity_catalog" {
  name                     = "stuc${substr(random_string.suffix.result, 0, 20)}"  # Max 24 chars, stuc = 4, suffix = 6, total = 10
  resource_group_name      = azurerm_resource_group.databricks.name
  location                 = azurerm_resource_group.databricks.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true  # Hierarchical namespace required for Unity Catalog
  min_tls_version          = "TLS1_2"

  # Enable public network access (can be restricted later)
  public_network_access_enabled = true

  tags = var.tags
}

# Storage Container for Unity Catalog
resource "azurerm_storage_container" "unity_catalog" {
  name                  = "unity-catalog"
  storage_account_name  = azurerm_storage_account.unity_catalog.name
  container_access_type = "private"
}

# Grant Storage Blob Data Contributor role to workspace managed identity
# Note: Azure Databricks workspaces use a system-assigned managed identity
# The role assignment may need to be done manually via Azure Portal or CLI
# After workspace creation, find the managed identity in the managed resource group
# and grant it "Storage Blob Data Contributor" role on the storage account
#
# Alternatively, you can use Azure CLI after apply:
# az role assignment create \
#   --role "Storage Blob Data Contributor" \
#   --assignee <workspace-managed-identity-object-id> \
#   --scope <storage-account-resource-id>
#
# For now, we'll create the storage account and note that manual assignment may be needed

# Unity Catalog Metastore
# NOTE: Requires account-level authentication - use account provider
#
# ALTERNATIVE: If account portal access fails, create metastore manually:
# 1. Go to your Databricks workspace UI
# 2. Settings → Data → Metastores → Create metastore
# 3. Use storage account: stuc<random-suffix> (see outputs)
# 4. Container: unity-catalog
# 5. Then uncomment the resources below and import: terraform import databricks_metastore.main <metastore-id>
#
resource "databricks_metastore" "main" {
  provider = databricks.account

  name          = "metastore-${var.environment}-${random_string.suffix.result}"
  storage_root  = "abfss://${azurerm_storage_container.unity_catalog.name}@${azurerm_storage_account.unity_catalog.name}.dfs.core.windows.net/"
  region        = azurerm_resource_group.databricks.location
  owner         = azuread_group.databricks_users.display_name
  force_destroy = true  # Allow deletion for dev environment

  depends_on = [
    azurerm_storage_container.unity_catalog
  ]

  # IMPORTANT:
  # 1. Account portal requires work/school Azure AD account (not personal Microsoft account)
  # 2. If you can't access account portal, create metastore manually via workspace UI
  # 3. Before creating the metastore, ensure the workspace's managed identity
  #    has "Storage Blob Data Contributor" role on the storage account
}

# Assign metastore to workspace
# For Azure Databricks, workspace_id is the numeric ID from the workspace URL
# Format: https://adb-<workspace-id>.<region>.azuredatabricks.net
# We extract the numeric workspace ID from the URL
locals {
  # Extract numeric workspace ID from URL
  # Azure Databricks URL format: https://adb-<workspace-id>.<numbers>.<region>.azuredatabricks.net
  # Extract the numeric ID after "adb-"
  workspace_url_parts = split(".", replace(azurerm_databricks_workspace.main.workspace_url, "https://", ""))
  workspace_subdomain = local.workspace_url_parts[0]  # e.g., "adb-1234567890123456"
  workspace_id        = replace(local.workspace_subdomain, "adb-", "")  # Extract just the numeric ID
}

# Metastore assignment also requires account-level authentication
resource "databricks_metastore_assignment" "main" {
  provider = databricks.account

  workspace_id         = local.workspace_id
  metastore_id         = databricks_metastore.main.id
  default_catalog_name = "main"

  depends_on = [
    databricks_metastore.main,
    azurerm_databricks_workspace.main
  ]
}

# Create initial catalog (optional but recommended)
resource "databricks_catalog" "main" {
  name    = "main"
  comment = "Main catalog for ${var.environment} environment"
  owner   = azuread_group.databricks_users.display_name

  depends_on = [
    databricks_metastore_assignment.main
  ]
}

# Create initial schema (optional but recommended)
resource "databricks_schema" "main" {
  catalog_name = databricks_catalog.main.name
  name         = "default"
  comment      = "Default schema for ${var.environment} environment"
  owner        = azuread_group.databricks_users.display_name

  depends_on = [
    databricks_catalog.main
  ]
}
