# Healthcare Data Generation Bundle

This is a Databricks Asset Bundle for generating synthetic healthcare/pharmaceutical distribution data for ML experimentation and analysis.

## Overview

This bundle generates realistic healthcare datasets for ML experimentation:
- **Pharmacies** (500 records) - Australian pharmacy chains and independents (large base entities)
- **Hospitals** (200 records) - Various hospital types across Australian states (large base entities)
- **Products** (5,000 records) - Comprehensive pharmaceutical product catalog
- **Orders** (25,000 records) - High volume of business transactions with discount logic
- **Inventory** (50,000 records) - Extensive stock management and reorder level data
- **Supply Chain Events** (10,000 records) - Rich logistics tracking with temperature monitoring

## Project Layout

```
.
├── README.md
├── databricks.yml
├── pyproject.toml
├── resources/
│   └── healthcare_data.job.yml      # Job configuration
└── src/
    ├── generate_catalog_data_static.py  # Main entry point (serverless job)
    ├── healthcare_data_generator.py     # Core data generation
    └── test_generator_local.py         # Local testing script
```

## Features

- **Realistic Data**: Australian context with PBS codes, ATC codes, and proper business logic
- **Unity Catalog Integration**: Saves data directly to `workspace.default.healthcare_*` tables
- **ML-Ready**: Supports all ML use cases from demand forecasting to fraud detection
- **Reproducible**: Seed-based generation for consistent results
- **Scalable**: Configurable dataset sizes for different environments
- **Serverless Compatible**: Uses proper environment specification with client 2 for maximum compatibility

## Getting Started

1. Install the Databricks CLI and log in:
   ```bash
   databricks configure --token
   ```

2. Deploy the bundle:
   ```bash
   databricks bundle deploy --target dev
   ```

3. Run the job:
   ```bash
   databricks bundle run
   ```

## Development

### Local Testing

1. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Test the data generator locally:
   ```bash
   python src/test_generator_local.py
   ```

3. Run tests:
   ```bash
   pytest
   ```

### Job Configuration

The job is configured for **large-scale data generation** for ML experimentation:

**Base Entities (Large Base - Created Once):**
- Pharmacies: 500
- Hospitals: 200

**Transactional Data (Large-Scale - Generated Once):**
- Products: 5,000
- Orders: 25,000  
- Inventory: 50,000
- Events: 10,000

**Total Dataset**: ~90,700 records for comprehensive ML training and analysis

You can modify these in `src/generate_catalog_data_static.py`.

### Generated Tables

Data is saved to Unity Catalog as:
- `workspace.default.healthcare_pharmacies`
- `workspace.default.healthcare_hospitals`
- `workspace.default.healthcare_products`
- `workspace.default.healthcare_orders`
- `workspace.default.healthcare_inventory`
- `workspace.default.healthcare_supply_chain_events`

Each table includes metadata columns (`_ingestion_timestamp`, `_source`) for data lineage tracking.

## ML Use Cases

This data supports all the ML scenarios outlined in the project:
- **Demand Forecasting**: Time-series data with seasonal patterns
- **Inventory Optimization**: Stock levels, reorder points, expiry tracking
- **Churn Prediction**: Customer behavior and order patterns
- **Recommender Systems**: Product-customer interaction data
- **Anomaly Detection**: Temperature monitoring and unusual patterns
- **Fraud Detection**: Order patterns and regulatory compliance
- **NLP Applications**: Special instructions and document processing