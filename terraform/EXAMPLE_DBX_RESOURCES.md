# Example: Comprehensive Databricks Workspace Management with Terraform

# 1. Workspace Infrastructure (Azure Provider)
resource "azurerm_databricks_workspace" "main" {
  name                = "databricks-${var.environment}"
  resource_group_name = azurerm_resource_group.databricks.name
  location            = azurerm_resource_group.databricks.location
  sku                 = var.databricks_sku
  tags                = var.tags
}

# 2. Databricks Provider Configuration
provider "databricks" {
  host = azurerm_databricks_workspace.main.workspace_url
}

# 3. Instance Pool for Cost Optimization
resource "databricks_instance_pool" "shared" {
  instance_pool_name = "shared-pool"
  min_idle_instances = 0
  max_capacity       = 10
  node_type_id       = "Standard_DS3_v2"
  idle_instance_autotermination_minutes = 10
}

# 4. All-Purpose Cluster
resource "databricks_cluster" "shared" {
  cluster_name            = "shared-cluster"
  spark_version           = "13.3.x-scala2.12"
  node_type_id            = "Standard_DS3_v2"
  driver_node_type_id     = "Standard_DS3_v2"
  num_workers             = 2
  autotermination_minutes = 20
  instance_pool_id        = databricks_instance_pool.shared.id

  spark_conf = {
    "spark.databricks.cluster.profile" = "singleNode"
    "spark.master"                     = "local[*]"
  }
}

# 5. Job Cluster
resource "databricks_cluster" "job" {
  cluster_name            = "job-cluster"
  spark_version           = "13.3.x-scala2.12"
  node_type_id            = "Standard_DS3_v2"
  driver_node_type_id     = "Standard_DS3_v2"
  num_workers             = 1
  autotermination_minutes = 10

  library {
    pypi {
      package = "pandas==1.5.3"
    }
  }

  library {
    pypi {
      package = "scikit-learn==1.3.0"
    }
  }
}

# 6. Scheduled Job
resource "databricks_job" "data_processing" {
  name = "daily-data-processing"

  new_cluster {
    num_workers   = 2
    spark_version = "13.3.x-scala2.12"
    node_type_id  = "Standard_DS3_v2"
  }

  notebook_task {
    notebook_path = "/Workspace/Shared/data_processing"
  }

  schedule {
    quartz_cron_expression = "0 0 9 * * ?"  # Daily at 9 AM
    timezone_id           = "UTC"
  }

  max_concurrent_runs = 1
}

# 7. Secret Scope
resource "databricks_secret_scope" "main" {
  name = "main-secrets"
}

# 8. Unity Catalog Setup
resource "databricks_catalog" "main" {
  name    = "main_catalog"
  comment = "Main catalog for ${var.environment} environment"
}

resource "databricks_schema" "main" {
  catalog_name = databricks_catalog.main.name
  name         = "main_schema"
  comment      = "Main schema for ${var.environment} environment"
}

# 9. SQL Warehouse
resource "databricks_sql_endpoint" "main" {
  name             = "main-warehouse"
  cluster_size    = "Small"
  min_num_clusters = 1
  max_num_clusters = 2
  auto_stop_mins   = 10
}

# 10. Global Init Script
resource "databricks_global_init_script" "main" {
  name     = "main-init-script"
  enabled  = true
  content_base64 = base64encode(<<-EOT
    #!/bin/bash
    pip install loguru
    EOT
  )
}

# 11. IP Access List
resource "databricks_ip_access_list" "main" {
  label = "main-access-list"
  list_type = "ALLOW"
  ip_addresses = [
    "0.0.0.0/0"  # Restrict this in production!
  ]
}
