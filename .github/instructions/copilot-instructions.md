---
applyTo: '**'
---

### Project Overview
- Purpose: Experimental platform for exploring Databricks functionality and implementing ML solutions for healthcare/pharmaceutical distribution scenarios
- Target Domain: EBOS-style supply chain, logistics, and healthcare analytics challenges
- Platform: Databricks free edition - `dbc-f501771e-54b7.cloud.databricks.com`
- Scope: Prototyping ML models, data engineering pipelines, and MLOps workflows

### Key Modelling Focus Areas
- Supply Chain Optimization: Demand forecasting, inventory management, logistics routing
- Healthcare Analytics: Churn prediction, market forecasting, recommender systems
- Operational Efficiency: Computer vision, anomaly detection, process optimization
- Regulatory Compliance: Fraud detection, document processing, compliance automation
- NLP Applications: Call center automation, document processing, product classification

### Technical Architecture
- Development Model: Local development with Databricks Connect for remote execution
  - use the `databricks-misc` conda env for any local run/dev
- Data Governance: Unity Catalog with three-level namespace (catalog.schema.table)
  - Unity Catalog demo catalog `ebos_uc_demo` (schemas per env/use-case); models often registered under `ebos_uc_demo.default`

### Code/Infrastructure Guidelines
- File Organization: Use flat structures where possible for Databricks compatibility
- Development Workflow: Local development → Databricks Connect → remote execution, generally assume we're running remotely unless otherwise specified
- Python Version: Ensure alignment between local and remote environments (noted as potential challenge)
- Performance: Databricks Connect is slower but more convenient than git-based workflows

### Data & ML Patterns
- Tree-based Methods: XGBoost/LightGBM for tabular operations data
- Time Series: Prophet, ARIMA, LSTM, Temporal Fusion Transformers for forecasting
- NLP: Transformers for document processing, call summarization

### Code Standards
- use KISS principles - keep it simple, stupid, we prefer straight forward/direct implementations that prioritize clarity over complexity
  - do not use `__init__.py` files unless absolutely necessary
- use DRY principles - don't repeat yourself, we prefer to reuse code/functions/classes/modules/etc. instead of duplicating code/functions/classes/modules/etc.
- if possible, use functions/functional programming instead of classes/object-oriented programming
- Logging: Always use loguru instead of print statements
- Module Structure: Prefer semantic naming (parent_module.semantic_name) over verbose names

### Misc
- Do not create unnecessary markdown/README files; we typically just one one root level README and then perhaps one in a major module ONLY if the complexity warrants it