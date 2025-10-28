# Databricks Infrastructure as Code

This directory contains Terraform configurations for deploying Databricks workspaces to Azure.

## Structure

- `environments/` - Environment-specific configurations (dev, staging, prod)
- `modules/` - Reusable Terraform modules
- `shared/` - Shared resources across environments

## Quick Start

### Prerequisites

1. Install Terraform CLI
2. Install Azure CLI and authenticate:
   ```bash
   az login
   az account set --subscription "your-subscription-id"
   ```

### Deploy Development Environment
```
# mac os local install
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

```bash
cd environments/dev
terraform init
terraform plan
terraform apply
```

### Deploy Other Environments

```bash
cd environments/staging
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## Cost Management

- Development environment uses `standard` SKU to minimize costs
- Production environments should use `premium` SKU for advanced features
- Consider implementing auto-termination policies for clusters
- Monitor costs using Azure Cost Management

## Security

- Each environment uses separate resource groups
- Managed resource groups are created automatically by Databricks
- Consider implementing network security groups for production environments

## Environment Variables

Set these environment variables for authentication:

```bash
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"
export ARM_SUBSCRIPTION_ID="your-subscription-id"
export ARM_TENANT_ID="your-tenant-id"
```

Or use Azure CLI authentication (recommended for development).

### Misc Learning
- `terraform init` - initializes the working directory, downloads required providers
  - "providers" are the plugins that Terraform uses to interact with the underlying infrastructure providers (e.g. Azure, AWS, GCP, etc.)
  - sets up teh backend for state storage
- `terraform plan` - shows what changes will be applied to the infrastructure
- `terraform apply` - applies the changes to the infrastructure
- statefile is a file that Terraform uses to track the current state of the infrastructure