# Databricks ML Experimentation Platform

## Project Overview

This project is an experimental platform for exploring Databricks functionality and implementing ML solutions for healthcare/pharmaceutical distribution scenarios. It combines **general-purpose data generation and domain modelling practice** with **specific use-cases** that consume shared data.

**Scope:**
- **Shared data foundation**: Synthetic healthcare data (generators + medallion) in `data/` — common to all use-cases. Use-cases may add inline transformations (e.g. derived columns for a given model) but do not duplicate raw/silver/gold pipelines.
- **Use-cases**: Each lives under `use_cases/<name>/` with its own DAB bundle (jobs, endpoints, interactive compute as needed). Examples: lunch-and-learn demos, recommender (train → MLflow → endpoints → app), demand forecasting, document intelligence.
- **Bundles**: Databricks Asset Bundle resources (jobs, endpoints, etc.) live under the use-case or data component they belong to — e.g. medallion jobs under `data/healthcare_data_medallion`, demand_forecasting jobs under `use_cases/demand_forecasting`. See `bundle_structure.md` for the pattern.

**Key Focus Areas:**
- Supply chain optimization (demand forecasting, inventory management, logistics routing)
- Healthcare customer analytics (churn prediction, market forecasting, recommender systems)
- Operational efficiency (computer vision, anomaly detection, process optimization)
- Regulatory compliance and fraud detection
- Natural language processing for document processing and customer support

**Technical Stack:**
- **Platform**: Databricks (free edition) - `dbc-f501771e-54b7.cloud.databricks.com`
- **Development**: Local development with Databricks Connect for remote execution
- **ML/AI**: PySpark MLlib, MLflow, Azure ML integration
- **Data**: Unity Catalog for data governance, flat file organization for Databricks compatibility

## Repo Structure

- **`data/`** — Shared data generators and medallion. Consumed by all use-cases.
  - `healthcare_data_generator` — DAB bundle; writes raw tables to Unity Catalog.
  - `healthcare_data_medallion` — DAB bundle; dbt bronze/silver/gold.
  - `prescription_pdf_generator` — General-purpose prescription PDF generation (no medallion). Document-intelligence annotation app lives under `use_cases/document_intelligence/annotator`.
- **`use_cases/`** — One directory per use-case; each can contain notebooks, apps, and its own DAB bundle (jobs/endpoints/interactive).
  - `lunch_and_learn` — Demos: lineage, dashboards, Genie, prediction-serving apps, synthetic data app.
  - `recommender` — Train models, MLflow, deploy endpoints, small Databricks app.
  - `demand_forecasting`, `document_intelligence`, etc.

## Todo List

### 🚀 Immediate Priorities
- [ ] **Unity Catalog Setup** - Set up Unity Catalog for data governance and organization
- [x] **Data Generation Pipeline** - Create synthetic healthcare/pharmaceutical datasets for experimentation
- [x] **Databricks Connect Setup** - Establish reliable local-to-remote development workflow
- [ ] **MLflow Integration** - Set up experiment tracking and model versioning

### 📊 Modelling & Data Science
- [ ] **Demand Forecasting Models** - Implement time-series forecasting (Prophet, XGBoost, LSTM)
- [ ] **Inventory Optimization** - Build constrained optimization models for stock replenishment
- [ ] **Churn Prediction** - Develop customer retention models for pharmacy/hospital clients
- [ ] **Anomaly Detection** - Create systems for detecting temperature excursions and suspicious orders

### 🛠️ Platform & Infrastructure
- [x] **DAB (Databricks Asset Bundles)** - Local and remote deployment workflows
- [ ] **Unity Catalog Organization** - Design catalog/schema structure for data governance
- [ ] **Azure Integration** - Terraform deployment for production-ready Databricks workspace
- [ ] **PostgreSQL Integration** - Connect external database to Databricks for data ingestion
- [x] **DBT Integration** - Data transformation and modeling workflows
- [ ] **CI/CD Pipelines** - CI/CD pipelines for the Databricks Asset Bundles

### 🔧 Development & Testing
- [ ] **PySpark Pipeline Development** - Segment work into manageable pipeline units
- [ ] **MLflow 3.0 Features** - Explore new capabilities and differences from previous versions
- [ ] **Databricks Connect Optimization** - Improve performance and reliability of local development
- [ ] **Python Version Alignment** - Ensure compatibility between local and remote environments