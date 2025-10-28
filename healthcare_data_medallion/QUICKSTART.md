# Healthcare Data Medallion Architecture - Quick Start Guide

## Overview
This DBT project implements a medallion architecture for healthcare/pharmaceutical distribution data, transforming raw data from the `healthcare_data` asset bundle into analytics-ready datasets.

## Architecture Layers

### 🥉 Bronze Layer
- **Purpose**: Raw data ingestion with minimal transformations
- **Location**: `models/bronze/`
- **Key Features**: Data lineage, ingestion timestamps, source tracking

### 🥈 Silver Layer  
- **Purpose**: Business logic, data quality, and standardization
- **Location**: `models/silver/`
- **Key Features**: Data validation, business rules, standardized naming

### 🥇 Gold Layer
- **Purpose**: Analytics-ready datasets for specific use cases
- **Location**: `models/gold/`
- **Key Datasets**:
  - Customer Analytics (pharmacy/hospital performance)
  - Product Analytics (product performance, demand patterns)
  - Supply Chain Analytics (order fulfillment, logistics)
  - Financial Analytics (revenue, discounts, profitability)
  - ML-Ready Datasets (feature-engineered for machine learning)

## Quick Start

### 1. Prerequisites
```bash
# Install DBT
pip install dbt-databricks

# Set your Databricks token
export DATABRICKS_TOKEN="your_token_here"
```

### 2. Configure Connection
Update `profiles.yml` with your Databricks warehouse ID:
```yaml
http_path: /sql/1.0/warehouses/YOUR_WAREHOUSE_ID
```

### 3. Run the Pipeline
```bash
# Test connection
dbt debug

# Run all models
dbt run

# Run tests
dbt test

# Generate documentation
dbt docs generate
dbt docs serve
```

### 4. Run Specific Layers
```bash
# Bronze layer only
dbt run --select tag:bronze

# Silver layer only  
dbt run --select tag:silver

# Gold layer only
dbt run --select tag:gold
```

## Data Flow
```
healthcare_data bundle → Unity Catalog → DBT Medallion Architecture
     ↓                        ↓                    ↓
Raw Data Generation    Raw Tables (Bronze)   Analytics Tables (Gold)
     ↓                        ↓                    ↓
workspace.default.      workspace.healthcare_   workspace.healthcare_
healthcare_*            medallion_dev.bronze.*  medallion_dev.gold.*
```

## Key Features
- **Data Quality**: Comprehensive validation and testing
- **Business Intelligence**: Customer, product, supply chain, and financial analytics
- **ML-Ready**: Feature-engineered datasets for machine learning
- **Data Lineage**: Complete tracking from source to gold layer
- **Automated Testing**: Data quality and business rule validation

## Use Cases
- **Business Intelligence**: Dashboards, reports, KPI tracking
- **Machine Learning**: Demand forecasting, churn prediction, inventory optimization
- **Regulatory Compliance**: Audit trails, compliance reporting, data governance

## Project Structure
```
healthcare_data_medallion/
├── dbt_project.yml              # DBT configuration
├── profiles.yml                 # Databricks connection
├── models/
│   ├── sources.yml             # Source definitions
│   ├── bronze/                 # Bronze layer models
│   ├── silver/                 # Silver layer models
│   └── gold/                   # Gold layer models
├── macros/                     # DBT macros
├── tests/                      # Data quality tests
└── README.md                   # Full documentation
```

## Support
For questions or issues, check the full README.md or contact the data engineering team.
