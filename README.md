# Databricks ML Experimentation Platform

## Project Overview

This project serves as an experimental platform for exploring Databricks functionality and implementing ML solutions for healthcare/pharmaceutical distribution scenarios. We're using the Databricks free edition to prototype various machine learning models and data engineering pipelines that could be applicable to EBOS's supply chain, logistics, and healthcare analytics challenges.

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

## Todo List

### 🚀 Immediate Priorities
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