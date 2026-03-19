# EBOS AI/ML platform

Implements **EBOS AI/ML use-cases** for healthcare/pharmaceutical distribution on **Databricks + Unity Catalog**: one shared data foundation (generators + medallion), use-cases on top.

- **Use-case spec:** [docs/EBOS_USE_CASES.md](docs/EBOS_USE_CASES.md) — data needs, modelling, architecture, file layout per use-case.
- **Data & platform:** [docs/DATA_AND_PLATFORM.md](docs/DATA_AND_PLATFORM.md) — UC layout, data flow, grants, data contracts, generator/medallion scope, local dev.

---

## Layout & stack

- **Use-cases:** `use_cases/<name>/` (recommendation_engine, inventory_optimization, document_intelligence, ai_powered_insights, etc.); each with DAB bundles (job, serving, app) as needed.
- **Data:** `data/healthcare_data_generator/`, `data/healthcare_data_medallion/`, `data/prescription_pdf_generator/`; [data/README.md](data/README.md) for generator → medallion locally.
- **Platform:** Databricks (free edition); Unity Catalog; dbt medallion (bronze/silver/gold); MLflow.

**Implemented:** Recommendation engine (item_similarity, ALS, LightFM, ranker); inventory optimisation (demand forecasting, write-off risk, replenishment); document intelligence (PDFs, OCR, annotator); AI insights (dashboards, Genie). Customer service agent and full insights apps in progress.

---

## Quick start

- **Env:** `make uv-venv`, `make install`, `make uv-dev`.
- **Data (local):** `make data-local-generate-quick`, `make data-local-duckdb-load`, `make data-local-dbt-run`.
- **Use-case e2e (local):** e.g. `make reco-local-e2e`, `make inventory-local-e2e` — run one at a time (shared DuckDB).
- **UC foundation:** `make uc-foundation-deploy` (then deploy generator/medallion/use-case bundles).

See [Makefile](Makefile) for all targets (`make help`).
