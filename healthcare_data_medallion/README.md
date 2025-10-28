# Healthcare Data Medallion Architecture

This DBT project implements a medallion architecture for healthcare/pharmaceutical distribution data, transforming raw data from the `healthcare_data` asset bundle into analytics-ready datasets.

## Architecture Overview

The medallion architecture consists of three layers:

### 🥉 Bronze Layer (Raw Data Ingestion)
- **Purpose**: Store raw data as-is with minimal transformations
- **Location**: `models/bronze/`
- **Tables**: Direct copies of source tables with metadata
- **Key Features**: Data lineage, ingestion timestamps, source tracking

### 🥈 Silver Layer (Business Logic & Data Quality)
- **Purpose**: Clean, validate, and apply business rules
- **Location**: `models/silver/`
- **Key Transformations**:
  - Data quality checks and validation
  - Standardized naming conventions
  - Business logic application
  - Data type standardization
  - Deduplication and data cleaning

### 🥇 Gold Layer (Analytics-Ready Datasets)
- **Purpose**: Business-ready datasets optimized for specific use cases
- **Location**: `models/gold/`
- **Key Datasets**:
  - **Customer Analytics**: Pharmacy/hospital performance metrics
  - **Product Analytics**: Product performance and categorization
  - **Supply Chain Analytics**: Order fulfillment and logistics metrics
  - **Financial Analytics**: Revenue, discounts, and profitability
  - **ML-Ready Datasets**: Feature-engineered data for machine learning

## Project Structure

```
healthcare_data_medallion/
├── dbt_project.yml              # DBT project configuration
├── profiles.yml                 # Databricks connection profiles
├── models/
│   ├── sources.yml             # Source table definitions
│   ├── bronze/                 # Bronze layer models
│   │   ├── bronze_pharmacies.sql
│   │   ├── bronze_hospitals.sql
│   │   ├── bronze_products.sql
│   │   ├── bronze_orders.sql
│   │   ├── bronze_inventory.sql
│   │   └── bronze_supply_chain_events.sql
│   ├── silver/                 # Silver layer models
│   │   ├── silver_pharmacies.sql
│   │   ├── silver_hospitals.sql
│   │   ├── silver_products.sql
│   │   ├── silver_orders.sql
│   │   ├── silver_inventory.sql
│   │   └── silver_supply_chain_events.sql
│   └── gold/                   # Gold layer models
│       ├── gold_pharmacy_performance.sql
│       ├── gold_product_performance.sql
│       ├── gold_supply_chain_performance.sql
│       ├── gold_financial_analytics.sql
│       └── gold_ml_ready_dataset.sql
├── macros/                     # DBT macros
│   └── data_quality_macros.sql
├── tests/                      # Data quality tests
│   └── generic_tests.sql
├── seeds/                      # Reference data
├── snapshots/                  # Slowly changing dimensions
└── analyses/                   # Ad-hoc analyses
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

### Data Quality & Validation
- Comprehensive data quality checks at each layer
- Business rule validation and enforcement
- Data lineage tracking throughout the pipeline
- Automated testing and monitoring

### Business Intelligence
- **Customer Analytics**: Pharmacy and hospital performance metrics
- **Product Analytics**: Product performance, demand patterns, profitability
- **Supply Chain Analytics**: Order fulfillment, delivery performance, logistics
- **Financial Analytics**: Revenue analysis, discount optimization, profitability

### Machine Learning Ready
- Feature-engineered datasets optimized for ML use cases
- Customer churn prediction features
- Product demand forecasting features
- Inventory optimization features
- Anomaly detection features

## Getting Started

### Prerequisites
- Databricks workspace access
- DBT CLI installed
- Python environment with required dependencies

### Setup

1. **Configure Databricks Connection**:
   ```bash
   # Set your Databricks token
   export DATABRICKS_TOKEN="your_token_here"
   
   # Update profiles.yml with your warehouse ID
   # Replace 'your_warehouse_id' with your actual warehouse ID
   ```

2. **Install Dependencies**:
   ```bash
   pip install dbt-databricks
   ```

3. **Run the Pipeline**:
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

### Running Specific Layers

```bash
# Run only bronze layer
dbt run --select tag:bronze

# Run only silver layer
dbt run --select tag:silver

# Run only gold layer
dbt run --select tag:gold

# Run specific model
dbt run --select gold_pharmacy_performance
```

## Configuration

### Variables
The project uses several configurable variables in `dbt_project.yml`:

- **Source Configuration**: Catalog, schema, and table prefixes
- **Data Quality Thresholds**: Min/max values for validation
- **Business Rules**: Discount thresholds, reorder alerts, expiry warnings

### Environment-Specific Settings
- **Dev Environment**: `healthcare_medallion_dev` schema
- **Prod Environment**: `healthcare_medallion_prod` schema

## Data Quality & Testing

### Automated Tests
- **Unique Constraints**: Primary key validation
- **Referential Integrity**: Foreign key validation
- **Data Range Validation**: Min/max value checks
- **Business Rule Validation**: Custom business logic tests

### Data Quality Metrics
- **Completeness**: Percentage of non-null values
- **Accuracy**: Data validation against business rules
- **Consistency**: Cross-table validation
- **Timeliness**: Data freshness monitoring

## Use Cases

### Business Intelligence
- **Executive Dashboards**: High-level KPIs and performance metrics
- **Operational Reports**: Detailed operational analytics
- **Financial Analysis**: Revenue, profitability, and discount analysis
- **Supply Chain Monitoring**: Order fulfillment and delivery performance

### Machine Learning
- **Demand Forecasting**: Product demand prediction models
- **Customer Churn Prediction**: Customer retention analysis
- **Inventory Optimization**: Stock level optimization
- **Anomaly Detection**: Unusual patterns and fraud detection
- **Recommender Systems**: Product recommendation engines

### Regulatory Compliance
- **Audit Trails**: Complete data lineage and change tracking
- **Compliance Reporting**: Regulatory requirement reporting
- **Data Governance**: Data quality and consistency monitoring

## Monitoring & Maintenance

### Data Lineage
- Complete tracking from source to gold layer
- Metadata preservation throughout the pipeline
- Change tracking and audit trails

### Performance Optimization
- Incremental model updates where appropriate
- Partitioning strategies for large tables
- Query optimization and indexing

### Error Handling
- Comprehensive error logging and monitoring
- Data quality alerts and notifications
- Automated retry mechanisms

## Contributing

1. Follow the established naming conventions
2. Add appropriate tests for new models
3. Update documentation for new features
4. Ensure data quality standards are maintained

## Support

For questions or issues:
1. Check the DBT documentation
2. Review the data quality tests
3. Examine the model lineage in DBT docs
4. Contact the data engineering team
