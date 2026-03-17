# EBOS AI/ML Technical Implementation Platform

This repository implements the **EBOS AI/ML Use Cases**: a set of use-cases for healthcare/pharmaceutical distribution (Databricks + Unity Catalog). All use-cases are of equal priority; implementation order may vary. It combines a **shared data foundation** (generators + medallion) with **use-cases** that consume that data — one data platform, many use-cases on top, mimicking real-life data generation and medallions.

**Full specification**: [docs/EBOS_USE_CASES.md](docs/EBOS_USE_CASES.md) (data requirements, modelling approach, architecture, file structure per use-case).  
**Data generator roadmap**: [docs/DATA_GENERATOR_DEV_PLAN.md](docs/DATA_GENERATOR_DEV_PLAN.md) (phased plan to implement all new data for use cases, extending the healthcare generator where possible).

---

## Infrastructure & layout

- **Infrastructure**: Databricks + Unity Catalog (`workspace.default` schema).
- **Repo layout**: Use-cases under `use_cases/<name>/`; DAB bundles (jobs, endpoints, interactive) live under each use-case or data component (see [example_bundles/bundle_structure.md](example_bundles/bundle_structure.md)).

**Existing assets**:
- Healthcare data generator with medallion architecture (bronze/silver/gold)
- Inventory optimisation: demand forecasting, write-off risk, replenishment (see `use_cases/inventory_optimization/models/`)
- Recommendation engine: item_similarity, ALS, LightFM, ranker (see `use_cases/recommendation_engine/models/`)
- Spark NLP setup for document intelligence in `use_cases/document_intelligence/`
- Prescription PDF generator in `data/prescription_pdf_generator/`; annotation app in `use_cases/document_intelligence/annotator/`

---

## Data strategy

- **Extend and consolidate** the existing `healthcare_data_generator` (and medallion) for reuse across use-cases where possible. New tables (e.g. substitution_events, product_interactions, expiry_batches, writeoff_events) will be added incrementally as use-cases are implemented.
- Use-cases may add inline transformations or derived columns; they do not duplicate raw/silver/gold pipelines.
- Separate generators/medallions only where the domain is orthogonal (e.g. customer service, document pipelines).

---

## Use-cases (EBOS shortlist)

| #     | Use-case                                                                                                    | Status                                 | Location                                                                                               |
| ----- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **1** | **Recommendation Engine for Ordering** — Similar products, auto-substitutions, margin-aware recommendations | ✅ Partial (item_similarity, ALS, LightFM, ranker) | `use_cases/recommendation_engine/` (`models/` for core, train, apply) |
| **2** | **Inventory Optimisation** — Demand forecasting, write-off risk, replenishment optimisation         | ✅ Partial (demand_forecasting, writeoff_risk, replenishment)  | `use_cases/inventory_optimization/` (`models/` for core, train, apply) |
| **3** | **AI Customer Service Agents** — Intent classification, RAG, order tracking                                 | ⚠️ Not implemented                      | `use_cases/customer_service_agent/`                                                                    |
| **4** | **Document Intelligence (Finance & Ordering)** — OCR, NER, invoice/PO extraction                            | ✅ Partial (Spark NLP setup, annotator) | `use_cases/document_intelligence/`                                                                     |
| **5** | **AI Powered Insights & Analytics** — Ranging/consolidation, market intelligence, franchise analytics       | ⚠️ Not implemented                      | `use_cases/ranging_consolidation/`, `use_cases/market_intelligence/`, `use_cases/franchise_analytics/` |

Details (data requirements, modelling, jobs, apps): see [docs/EBOS_USE_CASES.md](docs/EBOS_USE_CASES.md).

---

## Repo structure

```
databricks-misc/
├── data/                    # Shared data foundation
│   ├── healthcare_data_generator/   # DAB bundle; raw tables → Unity Catalog
│   ├── healthcare_data_medallion/   # DAB bundle; dbt bronze/silver/gold
│   └── prescription_pdf_generator/ # General-purpose prescription PDFs
│
├── use_cases/               # One directory per use-case (each with own DAB bundle as needed)
│   ├── recommendation_engine/          # config, app/; models/ (item_similarity, als, lightfm, ranker, run_reco, data_loading, etc.)
│   ├── inventory_optimization/         # config; models/ (demand_forecasting, writeoff_risk, replenishment)
│   ├── customer_service_agent/
│   ├── document_intelligence/      # includes annotator/
│   ├── ranging_consolidation/
│   ├── market_intelligence/
│   └── franchise_analytics/
│
├── docs/                    # Documentation
│   ├── EBOS_USE_CASES.md    # EBOS use-cases spec (source of truth)
│   ├── DATA_GENERATOR_DEV_PLAN.md  # Phased plan for new data (all use cases)
│   ├── GENERIC_MODELLING.md # Alternative / non-EBOS modelling options
│   └── LUNCH_AND_LEARN.md   # Session plan; to be aligned with EBOS use-cases
├── pyproject.toml           # UV / local deps
└── Makefile                 # cleanup, format, uv, document_intelligence generate_pdfs
```

**Lunch & Learn**: [docs/LUNCH_AND_LEARN.md](docs/LUNCH_AND_LEARN.md) is a standalone session plan; it will be revisited and aligned with the EBOS use-cases so demos draw on implemented capabilities.

---

## Technical stack

- **Platform**: Databricks (free edition) — `dbc-f501771e-54b7.cloud.databricks.com`
- **Development**: Local with Databricks Connect; UV env `databricks-misc` (see Makefile: `make uv-venv`, `make install`, `make uv-dev`)
- **Data**: Unity Catalog; dbt medallion (bronze → silver → gold)
- **ML**: MLflow, PySpark MLlib; model serving endpoints per use-case

---

## Todo (aligned with EBOS)

### Immediate
- [x] **Recommendation Engine** — Item similarity, ALS, LightFM, ranker under `models/`; run_reco pipeline; DAB jobs + endpoints
- [ ] **MLflow integration** — Experiment tracking and model registry across use-cases
- [ ] **Unity Catalog** — Catalog/schema organisation

### Next
- [x] **Inventory Optimisation** — Write-off risk, replenishment under `models/`; demand_forecasting in `models/demand_forecasting/`
- [ ] **Document Intelligence** — OCR/NER pipeline, exception review app
- [ ] **Customer Service Agent** — Intent + RAG + order tracking
- [ ] **Insights & Analytics** — Ranging, market intelligence, franchise analytics

### Platform
- [x] DAB (Databricks Asset Bundles) per use-case
- [x] DBT medallion