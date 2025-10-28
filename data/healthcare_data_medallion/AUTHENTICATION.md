# Databricks Authentication Options for DBT

This guide shows different ways to authenticate with Databricks from DBT, ordered by security best practices.

## 🔐 **Option 1: Environment Variables (Recommended)**

### Setup
```bash
# Set your Databricks token as an environment variable
export DATABRICKS_TOKEN="your_databricks_token_here"

# Or create a .env file
cp env.example .env
# Edit .env with your actual token
```

### profiles.yml
```yaml
healthcare_data:
  target: dev
  outputs:
    dev:
      type: databricks
      host: https://dbc-f501771e-54b7.cloud.databricks.com
      http_path: /sql/1.0/warehouses/2a475c6457a76313
      token: "{{ env_var('DATABRICKS_TOKEN') }}"
      schema: healthcare_medallion_dev
      catalog: workspace
```

### Pros
- ✅ Secure (token not in code)
- ✅ Easy to manage
- ✅ Works with CI/CD
- ✅ Can be overridden per environment

### Cons
- ❌ Need to set environment variable

---

## 🔐 **Option 2: Databricks CLI Profile**

### Setup
```bash
# Install Databricks CLI
pip install databricks-cli

# Configure profile
databricks configure --token
# Enter host: https://dbc-f501771e-54b7.cloud.databricks.com
# Enter token: your_token_here
```

### profiles.yml
```yaml
healthcare_data:
  target: dev
  outputs:
    dev:
      type: databricks
      host: https://dbc-f501771e-54b7.cloud.databricks.com
      http_path: /sql/1.0/warehouses/2a475c6457a76313
      token: "{{ env_var('DATABRICKS_TOKEN') }}"
      schema: healthcare_medallion_dev
      catalog: workspace
```

### Pros
- ✅ Uses existing Databricks CLI config
- ✅ Token stored securely in ~/.databrickscfg
- ✅ No hardcoded credentials

### Cons
- ❌ Requires Databricks CLI installation
- ❌ Less flexible for different environments

---

## 🔐 **Option 3: OAuth (Enterprise)**

### Setup
```bash
# Set OAuth environment variables
export DATABRICKS_CLIENT_ID="your_client_id"
export DATABRICKS_CLIENT_SECRET="your_client_secret"
```

### profiles.yml
```yaml
healthcare_data:
  target: dev
  outputs:
    dev:
      type: databricks
      host: https://dbc-f501771e-54b7.cloud.databricks.com
      http_path: /sql/1.0/warehouses/2a475c6457a76313
      client_id: "{{ env('DATABRICKS_CLIENT_ID') }}"
      client_secret: "{{ env('DATABRICKS_CLIENT_SECRET') }}"
      schema: healthcare_medallion_dev
      catalog: workspace
```

### Pros
- ✅ Most secure for enterprise
- ✅ No long-lived tokens
- ✅ Works with SSO

### Cons
- ❌ Complex setup
- ❌ Requires OAuth configuration

---

## 🔐 **Option 4: Azure Service Principal**

### Setup
```bash
# Set Azure environment variables
export AZURE_CLIENT_ID="your_client_id"
export AZURE_CLIENT_SECRET="your_client_secret"
export AZURE_TENANT_ID="your_tenant_id"
```

### profiles.yml
```yaml
healthcare_data:
  target: dev
  outputs:
    dev:
      type: databricks
      host: https://dbc-f501771e-54b7.cloud.databricks.com
      http_path: /sql/1.0/warehouses/2a475c6457a76313
      azure_client_id: "{{ env('AZURE_CLIENT_ID') }}"
      azure_client_secret: "{{ env('AZURE_CLIENT_SECRET') }}"
      azure_tenant_id: "{{ env('AZURE_TENANT_ID') }}"
      schema: healthcare_medallion_dev
      catalog: workspace
```

### Pros
- ✅ Enterprise-grade security
- ✅ Works with Azure AD
- ✅ No hardcoded credentials

### Cons
- ❌ Complex setup
- ❌ Requires Azure configuration

---

## 🚫 **Option 5: Hardcoded Token (NOT RECOMMENDED)**

### profiles.yml
```yaml
healthcare_data:
  target: dev
  outputs:
    dev:
      type: databricks
      host: https://dbc-f501771e-54b7.cloud.databricks.com
      http_path: /sql/1.0/warehouses/2a475c6457a76313
      token: "dapiac169e62479f9e9bb9214cc781534732"  # ❌ DON'T DO THIS
      schema: healthcare_medallion_dev
      catalog: workspace
```

### Cons
- ❌ Security risk
- ❌ Token exposed in code
- ❌ Hard to rotate
- ❌ Not suitable for production

---

## 🎯 **Recommendation**

For this project, we recommend **Option 1: Environment Variables** because:

1. **Security**: Token is not hardcoded in files
2. **Simplicity**: Easy to set up and manage
3. **Flexibility**: Can be overridden per environment
4. **CI/CD Friendly**: Works well with automated deployments
5. **Best Practice**: Follows DBT and Databricks security guidelines

## 🔧 **Getting Your Databricks Token**

1. Go to your Databricks workspace
2. Click on your username (top right)
3. Select "User Settings"
4. Go to "Developer" tab
5. Click "Generate new token"
6. Set expiration (recommend 90 days)
7. Copy the token and use it in your environment variable

## 📝 **Environment Variable Setup**

### For Development
```bash
# In your shell profile (~/.bashrc, ~/.zshrc, etc.)
export DATABRICKS_TOKEN="your_token_here"
```

### For Production/CI
```bash
# Set in your CI/CD environment variables
DATABRICKS_TOKEN=your_token_here
```

### For Local Development with .env
```bash
# Create .env file
echo "DATABRICKS_TOKEN=your_token_here" > .env

# Load in your shell
source .env
```
