output "databricks_workspace_url" {
  description = "URL of the Databricks workspace"
  value       = "https://${azurerm_databricks_workspace.main.workspace_url}/"
}

output "databricks_workspace_id" {
  description = "ID of the Databricks workspace"
  value       = azurerm_databricks_workspace.main.id
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.databricks.name
}

output "managed_resource_group_name" {
  description = "Name of the managed resource group"
  value       = azurerm_databricks_workspace.main.managed_resource_group_name
}
