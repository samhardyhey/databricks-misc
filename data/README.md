# Data foundation: generators and medallion

This directory holds the **shared data foundation** for EBOS use cases: synthetic data generators and the **medallion** (bronze → silver → gold) built with dbt. For generator/medallion scope, use-case→data mapping, and local dev, see [docs/DATA_AND_PLATFORM.md](../docs/DATA_AND_PLATFORM.md).

---

## Directory layout

| Path                            | Role                                                                                                                                                                              |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **healthcare_data_generator/**  | Python (pandas + Faker). Produces pharmacies, hospitals, products, orders, inventory, supply_chain_events (and later suppliers, warehouses, etc.). Output: CSVs or Unity Catalog. |
| **healthcare_data_generator/bundles/** | DAB: `databricks.yml` + `resources/*.yml` (same layout as `use_cases/*/bundles/job/`). Deploy raw generator jobs to Databricks.                                                  |
| **healthcare_data_medallion/**  | dbt project. Bronze → silver → gold on healthcare raw tables; sources in `src/models/sources.yml`, profile in `dbt_profiles/profiles.yml`.                                        |
| **healthcare_data_medallion/bundles/** | DAB: `databricks.yml` + `resources/*.yml` for the chained dbt job (bronze → silver → gold).                                                                                        |
| **prescription_pdf_generator/** | Synthetic prescription PDFs + JSON labels (files); no UC tables.                                                                                                                  |
| **local/**                      | Gitignored. Local generator output (CSVs) and optional local DB (e.g. `medallion.duckdb`) for local dbt.                                                                          |

---

## Local / remote data generation and medallion workflow

### 1. Data generation (source of truth)

| Step          | What happens                                                                                                                                                                                         |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Generator** | `healthcare_data_generator` — Python (pandas + Faker). Produces synthetic entities: pharmacies, hospitals, products, orders, inventory, supply_chain_events (and later suppliers, warehouses, etc.). |
| **Output**    | Either **CSV files** (e.g. `save_datasets(..., output_dir)`) or **Unity Catalog tables** (via `generate_catalog_data_static.py` + Spark).                                                            |

The same logical datasets can be written to **files** (local) or **catalog** (Databricks).

---

### 2. Medallion (bronze → silver → gold)

Single dbt project: `healthcare_data_medallion/`.

- **Sources** (`src/models/sources.yml`): one source per raw table (e.g. `healthcare_raw.healthcare_orders`). Schema name comes from `var('source_schema')` (e.g. `healthcare_dev_raw` on Databricks).
- **Bronze**: Raw copy + lineage metadata (`_ingestion_timestamp`, `_source`, `_batch_id`, `bronze_processed_at`). One model per source table; reads from `source('healthcare_raw', '...')`.
- **Silver**: Cleans and enriches (trim, round, `datediff`, flags, tiers). Reads from `ref('bronze_*')`, applies filters and business rules.
- **Gold**: Analytics-ready (e.g. `gold_ml_ready_dataset`, `gold_pharmacy_performance`, `gold_financial_analytics`). Reads from `ref('silver_*')`.

On Databricks, the job runs: bronze (run + test) → silver (run + test) → gold (run + test), with dependencies between layers.

---

### 3. Production path (Databricks)

1. **Generate**: Job runs `generate_catalog_data_static.py` → Spark writes to Unity Catalog, e.g. `workspace.healthcare_dev_raw.healthcare_*`.
2. **Medallion**: dbt profile `databricks` → `type: databricks`, same catalog, schema e.g. `healthcare_medallion_dev`. Sources point at `healthcare_dev_raw`; dbt writes bronze/silver/gold into `healthcare_medallion_*` (or equivalent).
3. **Use cases**: Read from gold (and silver) tables in Unity Catalog for training, dashboards, serving.

---

### 4. Local path (faster dev) — DuckDB and local dbt

Goal: run the **same medallion logic** locally to iterate on dbt and use-case code without Databricks.

| Step                            | What happens                                                                                                                                                                                                                                                        |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Generate locally**         | Run the generator (e.g. `test_generator_local.py` or a small script), write CSVs to `data/local/` (same shapes as production). No Spark, no catalog.                                                                                                                |
| **2. “Raw” in a local DB**      | Expose the same raw tables the medallion expects. **DuckDB**: create views (or tables) over CSVs with `read_csv_auto('...')` (or a small macro), so no separate “CSV → DB” ETL. **SQLite**: run a small script to create tables and load each CSV.                  |
| **3. Local dbt profile**        | Use a **DuckDB** profile in `healthcare_data_medallion/dbt_profiles/profiles.yml`: `type: duckdb`, `path: data/local/medallion.duckdb` (and optionally set a schema for raw vs medallion). Set **source_schema** so sources resolve to where raw tables/views live. |
| **4. Run the same dbt project** | From `healthcare_data_medallion/`: `dbt run --profile duckdb` (or `--target local`). dbt reads from the local “raw” layer and builds bronze → silver → gold in the same DuckDB file (or a dedicated schema). Full medallion locally.                                |
| **5. Dialect**                  | Medallion SQL is Spark-style (e.g. `current_timestamp()`, `datediff`). DuckDB is usually close; you may need a few small tweaks. Fix in models or a thin macro layer so one project can target both Databricks and DuckDB.                                          |

**DuckDB** = local DB that can treat CSVs as the raw layer (no extra load job) and run analytical SQL; **local dbt** = same dbt project and medallion layers, pointed at that DuckDB instead of Databricks.

---

### 5. End-to-end picture

```
[Generator]  -->  CSVs (data/local/)  -->  [DuckDB: raw views/tables]
     |                                              |
     | (production)                                  v
     v                                    [dbt --profile duckdb]
[Spark → Unity Catalog raw]                        |
     |                                              v
     v                                    [DuckDB: bronze / silver / gold]
[dbt --profile databricks]                                  |
     |                                                     v
     v                                            [Use-case code: pandas / notebooks]
[Unity Catalog: bronze / silver / gold]
     |
     v
[Use-case jobs / serving on Databricks]
```

---

### 6. Summary

- **Generation**: One generator; output is either CSVs (local) or Unity Catalog (production).
- **Medallion**: One dbt project, three layers (bronze → silver → gold), driven by sources and refs.
- **Local dev**: Generate to CSVs → put “raw” in **DuckDB** (views over CSVs or tables) → add a **DuckDB dbt profile** and set source/target schemas → run **local dbt** for a full medallion in DuckDB. Production keeps the Databricks profile and Unity Catalog.
