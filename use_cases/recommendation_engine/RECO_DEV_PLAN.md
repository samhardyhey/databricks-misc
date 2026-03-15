# Recommendation engine: local vs Databricks

Single pipeline (load → feature → train → evaluate) runs **locally** or **on Databricks**. Behaviour is switched by **config**, not by separate scripts. Same code path; only data loading and Spark usage differ.

## Config switch

- **config.get_config()** returns: `data_source` (`"local"` | `"catalog"`), `local_data_dir`, `catalog_schema`, `on_databricks`.
- **data_source** is resolved from **RECO_DATA_SOURCE**:
  - `auto` (default): use `catalog` when running on Databricks (`DATABRICKS_RUNTIME_VERSION` set), else `local`.
  - `local`: always load from CSV (e.g. for quick dev or when forcing local even on a cluster).
  - `catalog`: always load from Unity Catalog (e.g. Databricks Connect from your machine against remote tables).

## Environment variables

| Variable | Meaning | Default |
|----------|---------|---------|
| RECO_DATA_SOURCE | `local` \| `catalog` \| `auto` | `auto` |
| LOCAL_DATA_PATH | Directory for local CSVs (interactions, products, etc.) | repo `data/local` |
| RECO_CATALOG_SCHEMA | Catalog/schema for reco tables (e.g. `workspace.healthcare_medallion`) | `workspace.healthcare_medallion` |
| MLFLOW_TRACKING_URI | Override MLflow tracking (e.g. local path or custom server) | local: `LOCAL_DATA_PATH/mlruns`; Databricks: default |
| MLFLOW_REGISTRY_URI | Override MLflow model registry | local: none; Databricks: `databricks-uc` |

On Databricks, `auto` → `catalog`; locally, `auto` → `local`. Override to test catalog from local (e.g. Databricks Connect + `RECO_DATA_SOURCE=catalog`) or to force CSV on a job (`RECO_DATA_SOURCE=local` and provide CSVs).

## Local (quick dev)

1. Generate data: `make reco-data` (writes `data/local/*.csv`).
2. Run pipeline: `make reco-run` (runs `run_reco_local.py` → `run_reco.main()` with default config).
3. Config: `data_source=local`, data from `LOCAL_DATA_PATH` or `data/local`. No Spark.

## Remote (Databricks)

1. Medallion must be built so that **silver_reco_interactions**, **silver_products**, **gold_reco_training_base** (and optionally silver_orders) exist in the catalog/schema you use.
2. Deploy and run the same entrypoint as a **Databricks job**: point the job’s Python task at `use_cases/recommendation_engine/run_reco.py` (repo root as working directory / source).
3. On the cluster, `DATABRICKS_RUNTIME_VERSION` is set → `auto` → `data_source=catalog`. Spark is created in `run_reco.main()` if not passed in; data is loaded via `load_reco_data(config, spark)` from Unity Catalog.
4. Optionally set **RECO_CATALOG_SCHEMA** in the job environment if your medallion uses a different catalog/schema.

## Technicalities

- **Single entrypoint**: `run_reco.py` is the main script; `run_reco_local.py` is a thin wrapper that calls `run_reco.main()` (kept for `make reco-run` and habit).
- **Data loading**: `data_loading.load_reco_data(config, spark)` returns the same dict shape (`interactions`, `products`, `orders`, `training_base`) whether data came from CSV or catalog. Downstream code does not branch on environment.
- **Spark**: Only required when `data_source == "catalog"`. On Databricks, `run_reco.main()` creates a SparkSession when needed; for jobs, the cluster already provides one and the script can use it.
- **Paths**: All path and schema choices live in `config.get_config()`; data_loading and run_reco use that only. No hardcoded local/catalog branches outside config and load_reco_data.

## Summary

| Run context | RECO_DATA_SOURCE | Data from | Spark |
|-------------|------------------|-----------|--------|
| Local (make reco-run) | auto → local | data/local CSV | No |
| Databricks job/notebook | auto → catalog | Unity Catalog | Yes (getOrCreate) |
| Local + catalog (e.g. Connect) | catalog | Unity Catalog | Yes (you pass or create) |
| Job forcing CSV | local | CSVs in workspace/path | No (if you ship CSVs) |

This keeps one codebase, fast local iteration, and the ability to run the same pipeline on Databricks with catalog data by switching config only.

## Optional deps and MLflow

- **Reco optional deps**: `implicit`, `lightgbm` are in the project’s `[reco]` extra (`pip install .[reco]`). The ALS and ranker modules import them directly; if you don’t install `[reco]`, `run_reco` still runs item_similarity and skips ALS when the import fails.
- **MLflow**: ALS and ranker trainers log model artefacts, pyfunc, and metrics when `log_to_mlflow=True`. **MLflow config** switches with environment (same as data source):
  - **Local**: tracking URI = `local_data_dir/mlruns` (or `MLFLOW_TRACKING_URI`); no registry URI (models only in local mlruns).
  - **Databricks**: tracking URI left at workspace default; registry URI = `databricks-uc` so models can be registered in Unity Catalog.
  - Override with **MLFLOW_TRACKING_URI** and **MLFLOW_REGISTRY_URI** if needed. `config.apply_mlflow_config()` is called by the trainers before logging.
