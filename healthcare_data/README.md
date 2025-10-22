# Healthcare Data Generation Bundle

This is a Databricks Asset Bundle for generating synthetic healthcare/pharmaceutical distribution data for ML experimentation and analysis.

## Overview

This bundle generates realistic healthcare datasets simulating a high-frequency system:
- **Pharmacies** (50 records) - Australian pharmacy chains and independents (stable base entities)
- **Hospitals** (25 records) - Various hospital types across Australian states (stable base entities)
- **Products** (25/15min = 100/hour) - New pharmaceutical products added regularly
- **Orders** (125/15min = 500/hour) - High volume of business transactions with discount logic
- **Inventory** (250/15min = 1,000/hour) - Frequent stock management updates and reorder levels
- **Supply Chain Events** (50/15min = 200/hour) - Continuous logistics tracking with temperature monitoring

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

The job is configured to run **every 15 minutes** and generates data using a high-frequency strategy:

**Base Entities (Stable - Created Once):**
- Pharmacies: 50
- Hospitals: 25

**Transactional Data (High-Frequency - Appended Every 15 Minutes):**
- Products: 25/15min (100/hour)
- Orders: 125/15min (500/hour)
- Inventory: 250/15min (1,000/hour)
- Events: 50/15min (200/hour)

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