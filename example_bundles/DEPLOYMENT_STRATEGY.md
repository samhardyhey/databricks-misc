# HPS Clinical Notes JSL Pipeline - Databricks Asset Bundles

This directory contains three separate Databricks Asset Bundles for deploying the HPS Clinical Notes JSL Pipeline components independently.

## Overview

The solution is split into **3 separate bundles** for clean deployment separation:

### **Jobs Bundle** (`bundles/jobs/`)
- **Batch Processing Pipeline**: Job with JSL-optimized compute cluster
- **Deployment Targets**: dev-sp, test-sp, prod-sp
- **Resource**: Batch processing job definition

### **Endpoints Bundle** (`bundles/endpoints/`)
- **Model Serving**: VLM model serving for medical document processing  
- **Deployment Targets**: dev-sp, test-sp, prod-sp
- **Resource**: Model serving endpoint definition

### **Interactive Bundle** (`bundles/interactive/`)
- **Development Clusters**: DBR1 & DBR2 for interactive JSL development
- **Deployment Targets**: prod-sp (temporary), dev-sp (future)
- **Resource**: Interactive cluster definitions

## Bundle Architecture Benefits

✅ **Independent Deployment**: Deploy jobs, endpoints, and clusters separately  
✅ **Environment Isolation**: Each bundle supports dev/test/prod targeting  
✅ **Resource Separation**: Clean boundaries between components  
✅ **Lifecycle Management**: Different deployment schedules for different components

## Environment/DAB Resource Strategy

### Standard Resource Pattern
Each environment (`dev-sp`, `test-sp`, `prod-sp`) will feature:

**Endpoint**: VLM model serving endpoint with GPU_LARGE workload type, scale-to-zero enabled (0-4 max concurrency), hosting jsl-vlm-8b model version 2

**Job Compute**: Standard_E16_v3 single node cluster (16 cores, 128GB RAM) running Databricks Runtime 16.4.x-cpu-ml-scala2.12 with JSL-optimized Spark configurations

**Dev Environment Extension**: The dev environment will additionally feature two interactive compute clusters (DBR1 & DBR2) using the same Standard_E16_v3 specification as job compute, configured for persistent interactive development

### Caveats & Current State

**Environment Maturity**:
- **Prod-SP**: Fully operational with existing job + endpoint resources
- **Dev-SP & Test-SP**: Under construction, will implement above pattern when infrastructure is available
- **Temporary Workaround**: Interactive compute clusters (DBR1 & DBR2) will be deployed to prod environment until dev/test environments are accessible

**License Management**:
- **Current**: Single license set (10753) shared across all environments and compute types
- **Target**: Separate JSL license keys per environment AND per compute instance (job compute, interactive clusters, endpoints) for proper isolation

**Deployment Strategy**:
- Job compute already parameterized for cross-environment deployment using `${var.schema}` and environment variables
- Interactive clusters will target `dev-sp` environment only (temporarily deployed to `prod-sp`)
- All compute resources share the same base specification (Standard_E16_v3, single node) for consistency

**Required DAB Updates**:
1. ✅ **Separate Deployment Targets**: Created dedicated targets for jobs, endpoints, and interactive clusters
2. ✅ **Interactive Cluster Definitions**: Added DBR1 & DBR2 interactive clusters (temporarily targeting prod)
3. Expand license variable structure for per-environment, per-compute-type keys  
4. Update endpoint resources to use environment-specific license injection

**Naming Convention**: Maintain `-sp` suffixes for all environment targets

## Prerequisites

### 1. Library Files
Ensure the following files are available in the workspace:

**Wheel Files (Workspace):**
- `/Workspace/HPS_Clinical_Notes_Discover/JSL/spark_ocr-6.2.0rc1-py3-none-any.whl`
- `/Workspace/HPS_Clinical_Notes_Discover/JSL/spark_nlp_jsl-6.0.0-py3-none-any.whl`

**JAR Files (Volumes):**
- `/Volumes/hps_clinical_notes_discover/custom/libraries/spark-nlp-assembly-6.0.0.jar`
- `/Volumes/hps_clinical_notes_discover/custom/libraries/spark-ocr-assembly-6.0.0.jar`
- `/Volumes/hps_clinical_notes_discover/custom/libraries/spark-nlp-jsl-6.0.0.jar`

### 2. Key Vault Secrets
Configure the following secrets in the key vault `hps-clinical-notes-kv`:
- `spark-nlp-license`: Spark NLP license key
- `spark-ocr-license`: Spark OCR license key  
- `aws-access-key-id`: AWS access key for S3 access
- `aws-secret-access-key`: AWS secret key for S3 access

**Note**: These are automatically referenced through bundle variables, making them reusable and maintainable.