# Local Development Review

Review of the codebase for running **data generation**, **medallion creation**, and **model training / MLflow** locally (including SQLite or file-based alternatives), and which aspects of each EBOS use case can be developed locally.

---

## 1. Data generation and medallion creation — local / SQLite?

**Recommendation**: Raw CSVs in a gitignored directory (e.g. `data/local/`) are sufficient for local use-case development—simplest, transparent, and fast. No SQLite required for data loading or model training. **Optional**: a dbt-sqlite profile exists for running the medallion locally when you need bronze/silver/gold tables in a DB; you must populate the SQLite DB from CSVs first (e.g. via a small script). The Databricks profile is kept for production.

### 1.1 Healthcare data generator

| Component          | Location                                                          | Local?  | Notes                                                                                        |
| ------------------ | ----------------------------------------------------------------- | ------- | -------------------------------------------------------------------------------------------- |
| **Core generator** | `data/healthcare_data_generator/src/healthcare_data_generator.py` | **Yes** | Pure pandas + Faker. No Spark, no DB.                                                        |
| **Save output**    | `save_datasets(..., output_dir)`                                  | **Yes** | Writes **CSV** files under `output_dir`.                                                     |
| **Local test**     | `data/healthcare_data_generator/src/test_generator_local.py`      | **Yes** | Runs generator and export to CSV; run from repo root with `PYTHONPATH` or installed package. |

So **data generation** can be run fully locally: use `HealthcareDataGenerator` and `save_datasets()` to get CSV files (e.g. under `data/` or a local `data/healthcare_raw/`). No SQLite is required; CSVs are the current local output.

### 1.2 Ingesting into a catalog (Databricks vs local)

| Component             | Location                                                             | Local? | Notes                                                                                                     |
| --------------------- | -------------------------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------- |
| **Databricks ingest** | `data/healthcare_data_generator/src/generate_catalog_data_static.py` | **No** | Uses **Spark** and writes to **Unity Catalog** (`workspace.{schema}.healthcare_*`). No local/SQLite path. |

So **“medallion input” creation** (raw tables in a catalog) is Databricks-only today. For a local equivalent you could:

- **Option A**: Keep using CSVs as the “raw” layer and skip Spark for local dev.
- **Option B**: Add a small script that writes generator output to **SQLite** (e.g. one table per entity) so local tools (dbt-sqlite, pandas, or a local Spark H2/SQLite backend) can read from a DB instead of CSV. Not implemented today.

### 1.3 Medallion (dbt) — can it run locally on SQLite?

| Item            | Current state                                                                                            | Local / SQLite?                                                                 |
| --------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **dbt project** | `data/healthcare_data_medallion/`                                                                        | —                                                                               |
| **Profile**     | `profile: databricks` in `dbt_project.yml`                                                               | **Databricks only**                                                             |
| **Target**      | `dbt_profiles/profiles.yml` → `type: databricks`, `catalog: workspace`, `schema: healthcare_medallion_*` | **Unity Catalog**                                                               |
| **Sources**     | `source('healthcare_raw', 'healthcare_orders')` etc. in `src/models/sources.yml`                         | Resolve to **Databricks schema** (`var('source_schema', 'healthcare_dev_raw')`) |
| **SQL**         | Standard SQL + `current_timestamp()`; no Delta-specific syntax in models                                 | Dialect is Spark/Databricks; some functions may differ on SQLite                |

**Conclusion**: The medallion is wired for **Databricks (Delta/Unity Catalog)**. It does **not** run on SQLite as-is because:

1. There is no dbt-sqlite (or other local) profile; only `databricks` with HTTP + token.
2. Sources point at Unity Catalog schemas, not local DBs or files.
3. dbt-databricks writes Delta tables; SQLite would require a different adapter and schema setup.

To run medallion “locally” you would need at least:

- A **separate dbt profile** (e.g. `sqlite` or `duckdb`) and schema names that point to local DBs or file-based datasets.
- **Source tables** in that DB (e.g. populated from the generator’s CSVs → SQLite/DuckDB).
- Possible **SQL dialect** tweaks (e.g. `current_timestamp()` and any Spark-only functions).

So: **data generation can run locally (CSV); medallion creation as implemented runs only on Databricks; running the same dbt medallion on SQLite would require additional wiring (profile, sources, dialect).**

---

## 2. Train models / save to MLflow locally

### 2.1 Data loading — local vs remote

| Component                    | Location                                                     | Behavior                                                                                                                                                                                                   | Local?      |
| ---------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| **Demand forecasting entry** | `use_cases/demand_forecasting/run_forecasting_experiment.py` | Creates **SparkSession**; tries `load_healthcare_data(spark)` → `spark.table("workspace.default.healthcare_orders").toPandas()`; on **exception** falls back to `create_sample_data()` (in-memory pandas). | **Partial** |
| **Sample data**              | `create_sample_data()` in same file                          | Builds a pandas DataFrame (synthetic time series). No Spark, no catalog.                                                                                                                                   | **Yes**     |

So:

- There is **no** explicit “if local then load from CSV/SQLite” path. The script **always** starts Spark and tries Unity Catalog first; only if that **fails** does it use sample data.
- To run **fully locally** without Spark you would need to:
  - Either add a branch that skips Spark and loads from **CSV** (or SQLite) when e.g. `RUN_LOCAL=1` or `DATA_PATH=...`, or
  - Run with Spark disabled/failing so it always uses `create_sample_data()`.

Downstream (e.g. `model_comparison.run_full_comparison`, `data_preparation.prepare_forecasting_data`) already work on pandas DataFrames, so once you have a DataFrame (from CSV, SQLite, or sample data), the rest is local-friendly.

### 2.2 MLflow tracking and model saving

| Item               | Location                                                                                     | Behavior                                                                                                                                      | Local?              |
| ------------------ | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| **Tracking URI**   | —                                                                                            | **Not set** in codebase (no `mlflow.set_tracking_uri(...)`). So MLflow uses **default**: when not on Databricks that is **local `./mlruns`**. | **Yes** (local dir) |
| **Experiments**    | `model_comparison.py`, `xgboost_forecaster.py`, `ets_forecaster.py`, `prophet_forecaster.py` | `mlflow.set_experiment(...)`, `mlflow.start_run()`, `mlflow.log_*`, `mlflow.xgboost.log_model` etc.                                           | **Yes**             |
| **Model registry** | —                                                                                            | No Unity Catalog model registration in the reviewed code (only logging to MLflow).                                                            | N/A                 |

So:

- **Train models locally**: Yes — the forecasting code is pandas + sklearn/xgboost/prophet/statsmodels; no Spark in the model code.
- **Save to MLflow locally**: Yes — with default tracking URI, runs and artifacts go to `./mlruns` (or set `MLFLOW_TRACKING_URI` to another path or server).
- **If running on Databricks**: The same code will use the workspace MLflow tracking when executed there; no code change required.

**Summary**: Training and MLflow logging work locally (local `./mlruns`). There is no “if local then save models differently” logic; the only gap is **data loading**: add an explicit local path (CSV/SQLite or env flag) to avoid requiring Spark and Unity Catalog for local runs.

---

## 3. EBOS use cases — what can be devved locally (from EBOS_USE_CASES.md)

| Use case                          | Local-dev friendly? | What can be done locally                                                                                                                   | What needs Databricks / remote                                                                                                                           |
| --------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Recommendation Engine**      | **Mostly yes**      | Item-item (sklearn), ALS (implicit), LGBMRanker (LightGBM) on DataFrames; feature engineering and evaluation scripts.                      | Gold tables today are in Unity Catalog; batch scoring job and Model Serving endpoint are Databricks.                                                     |
| **2. Inventory Optimisation**     | **Mostly yes**      | Reuse demand forecasting (same as above). Write-off classifier (sklearn/LightGBM), replenishment (scipy/pulp) — all pandas + local MLflow. | Gold tables, scheduled jobs, dashboards.                                                                                                                 |
| **3. AI Customer Service Agents** | **Partly**          | Intent classifier (sklearn/transformers), RAG (sentence-transformers + local vector store e.g. Chroma/FAISS), agent logic, evaluation.     | Spec uses “Databricks Vector Search”; for local, swap to Chroma/FAISS + same embeddings. LLM (OpenAI/Databricks) can be called from local with API keys. |
| **4. Document Intelligence**      | **Partly**          | PDF generation already has `generate_prescription_pdfs_local.py`; annotation app can run locally.                                          | OCR/NER pipeline is **Spark OCR + Spark NLP** — needs Spark (local Spark or Databricks). NER training and batch pipelines are Databricks-oriented.       |
| **5. Insights & Analytics**       | **Mostly yes**      | Ranging (sklearn, scipy), market intel (scraping + optional LLM), franchise (sklearn, causalml) — all runnable on pandas + local files.    | Gold tables, scheduled jobs, Databricks SQL dashboards.                                                                                                  |

So:

- **Recommendation, inventory, insights**: Model training, evaluation, and feature code can be developed locally with CSV/DataFrame (or SQLite if you add it). Only orchestration and serving assume Databricks.
- **Customer service**: Same for intent and RAG logic; use a local vector store instead of Databricks Vector Search for dev.
- **Document intelligence**: Local for PDFs and annotation; OCR/NER pipeline assumes Spark (local or remote).

---

## 4. Recommendations

1. **Data generation**
   - Already local (CSV). Optional: add a small script to load CSVs into **SQLite** (one table per entity) for a single “local raw DB” if you want to mimic a catalog locally.
2. **Medallion**
   - Keep current dbt project for Databricks. If you want a local medallion: add a dbt profile (e.g. DuckDB or SQLite), point sources at local DB/file paths, and adjust SQL dialect if needed.
3. **Demand forecasting (and similar use cases)**
   - Add an explicit **local data path** (e.g. env `RUN_LOCAL=1` and `DATA_PATH=.../data` or path to SQLite): when set, skip creating Spark and load from CSV (or SQLite) into a pandas DataFrame. Keep existing `create_sample_data()` as fallback when no path is provided.
4. **MLflow**
   - No change needed for local training; defaults to `./mlruns`. Optionally document `MLFLOW_TRACKING_URI` for a local server or path. Only add “save differently when local” if you later introduce Unity Catalog model registration (then: if local, skip registration or use a local registry).
5. **Use-case implementations**
   - When implementing recommendation, inventory, customer service, insights: structure code so that **data input** is a DataFrame or path (CSV/SQLite); keep “load from Unity Catalog” in a thin adapter or job entrypoint. That keeps core logic local-dev friendly while still running on Databricks in production.

This review is based on the codebase as of the current repo state and [docs/EBOS_USE_CASES.md](EBOS_USE_CASES.md).
