# HPS Clinical Notes Interactive Bundle

This bundle deploys interactive development clusters for JSL experimentation and development.

## ⚠️ DAB Limitations (as of Feb 12, 2026)
**Important**: Databricks Asset Bundles do not support specifying `libraries` as part of interactive compute resource definitions. Libraries can only be specified in job cluster configurations within DAB.

For interactive clusters with pre-installed libraries, use the Python SDK management script: `manage_clusters.py`

## Resources
- **DBR1 Interactive**: Development cluster with JSL configuration (10609 license set) 
- **DBR2 Interactive**: Development cluster with JSL configuration (10753 license set)
- **Compute**: Standard_E16_v3 single node clusters (16 cores, 128GB RAM)
- **Runtime**: Databricks Runtime 16.4.x-cpu-ml-scala2.12

## Deployment Options

### Option 1: DAB Deployment (Clusters Only)
Deploy clusters without libraries using Databricks Asset Bundle:

```bash
cd bundles/interactive
databricks bundle deploy --target prod-sp --profile prod-sp
databricks bundle validate --target prod-sp --profile prod-sp
```

### Option 2: Python SDK Management (Clusters + Libraries)
Use the Python script for complete cluster management with JSL libraries:

```bash
cd bundles/interactive

# Create clusters with JSL libraries
python manage_clusters.py create --target prod-sp --profile prod-sp

# Check cluster status and library installation
python manage_clusters.py status --target prod-sp --profile prod-sp

# Install libraries on existing cluster
python manage_clusters.py install-libraries --cluster-name "HPS-DBR1-Interactive-prod" --profile prod-sp

# Delete clusters
python manage_clusters.py delete --target prod-sp --profile prod-sp
```

## Deployment Targets
- `prod-sp`: Production environment (temporary workaround - default)
- `dev-sp`: Development environment (future target when available)

## Features
- **Auto-Termination**: DBR1 (1 hour), DBR2 (2 hours) for cost control
- **JSL Ready**: Pre-configured with JSL-optimized Spark settings
- **License Integration**: Separate JSL license sets (10609 for DBR1, 10753 for DBR2)
- **Single Node**: Optimized for individual development work
- **Library Management**: Complete JSL library stack via SDK script

## JSL Libraries Included (via SDK Script)
- **Wheel Libraries**: spark_ocr-6.2.0rc1, spark_nlp_jsl-6.0.0
- **JAR Libraries**: spark-nlp-assembly-6.0.0, spark-ocr-assembly-6.0.0, spark-nlp-jsl-6.0.0  
- **PyPI Packages**: spark-nlp==6.0.0, pandas==1.5.3, numpy==1.26.4, openpyxl==3.1.5, RapidFuzz==3.14.3, opencv-python-headless==4.8.1.78

## Manual Cluster Management
```bash
# Using Databricks CLI (for DAB-created clusters without libraries)
databricks clusters start --cluster-id <cluster-id> --profile prod-sp
databricks clusters terminate --cluster-id <cluster-id> --profile prod-sp
databricks clusters list --profile prod-sp
```

## Requirements
- **Python SDK**: `pip install databricks-sdk`
- **Databricks CLI**: Configured with appropriate profile
- **Dependencies**: 
  - Shared source code: `../../src/`
  - Shared notebooks: `../../notebooks/`
  - Key vault secrets: JSL license keys and AWS credentials
  - JSL libraries: Available in workspace and Unity Catalog volumes

## Migrate from DAB to SDK
If you have existing DAB-deployed clusters without libraries:

1. **Check current status**: `python manage_clusters.py status --target prod-sp --profile prod-sp`
2. **Install libraries on existing clusters**: `python manage_clusters.py install-libraries --cluster-name "HPS-DBR1-Interactive-prod" --profile prod-sp`
3. **Or recreate with libraries**: 
   ```bash
   databricks bundle destroy --target prod-sp --profile prod-sp
   python manage_clusters.py create --target prod-sp --profile prod-sp
   ```