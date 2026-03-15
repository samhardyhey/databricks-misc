# Bundle integration dev plan: data generation, medallion, recommendation engine, inventory optimization

This document scopes how to integrate the **example bundles** pattern with the existing **healthcare data generator**, **healthcare data medallion**, **recommendation_engine**, and **inventory_optimization** use cases so that all can be deployed and run on Databricks in a consistent way, while keeping local dev (Makefile, DuckDB, CSV) unchanged.

**Reference**: [example_bundles/](../example_bundles/) — jobs bundle (batch + scheduling), endpoints bundle (model serving), interactive bundle (dev clusters); separate bundles per concern, **3-env targets** (dev-sp, test-sp, prod-sp), shared `variables`, `sync` of parent code.

**Chosen approach (Option B, refined)**: Four **separate bundles**, each **co-located with its code** (no top-level `bundles/`). Data generator and medallion stay under `data/`; recommendation engine and inventory optimization each get their own `databricks.yml` and `resources/` inside `use_cases/<use_case>/`. All bundles use the **3-env targets** (dev-sp, test-sp, prod-sp) from the example for workspace host, root_path, and variable overrides.

---

## 1. Example bundles pattern (summary)

| Aspect | Example (HPS Clinical Notes) | Our current state |
|--------|-----------------------------|-------------------|
| **Bundle split** | 3 bundles: jobs, endpoints, interactive | 2 bundles: healthcare_data_generator, healthcare_data_medallion |
| **Job definition** | YAML in `jobs/resources/*.yml`; notebook_task / spark_python_task; job_clusters; env vars from variables | Generator: spark_python_task + env; Medallion: dbt_task with bronze → silver → gold deps |
| **Targets** | dev-sp, test-sp, prod-sp: workspace host, root_path, variables (catalog, schema, secrets); mode development vs production; run_as service_principal | dev (default), prod; single workspace → **migrate to dev-sp / test-sp / prod-sp** |
| **Variables** | catalog, schema, service_principal_name, secrets, endpoint_* | (none in our bundles; dbt uses profile) |
| **Sync** | `sync.paths: ../../notebooks, ../../src` | Generator/medallion live under `data/`; use_cases at repo root |
| **Run order** | Jobs are independent or scheduled; endpoint jobs (startup/shutdown) are separate | Generator job runs on schedule; medallion job has no upstream dependency on generator in DAB |

**Takeaways for integration**:
- **Four separate bundles**, each **local to its code**: data generator, medallion, recommendation engine, inventory optimization (no shared EBOS ML bundle).
- Use **3-env targets** (dev-sp, test-sp, prod-sp) in every bundle: workspace host, root_path `.../.bundle/${bundle.name}/${bundle.target}`, variables (catalog, schema, etc.), mode (development vs production), run_as where applicable.
- Introduce **variables** (catalog, schema, source_schema, medallion_schema as needed per bundle) so config is env-driven.
- **Sync** only paths relative to each bundle (e.g. from `use_cases/recommendation_engine/`, sync `../..` or `../../data` if needed) so job code is available in workspace after deploy.
- Each use-case bundle defines **job(s)** that run its entrypoint (e.g. `run_reco.py`, `run_inventory.py`) with RECO_* / INVENTORY_* set from bundle variables.

---

## 2. Current state

### 2.1 Data generation and medallion

- **healthcare_data_generator** (`data/healthcare_data_generator/`)
  - **Bundle**: `databricks.yml`; targets dev (default), prod; single job `healthcare_data_generator_job` (spark_python_task → `generate_catalog_data_static.py`), schedule every 15 min.
  - **Output**: Writes to Unity Catalog (catalog/schema from script env, e.g. `workspace.healthcare_dev_raw`).
- **healthcare_data_medallion** (`data/healthcare_data_medallion/`)
  - **Bundle**: `databricks.yml`; targets dev, prod; job `healthcare_data_medallion_job` with three dbt_task steps (bronze → silver → gold), each `dbt deps`, `dbt run --select tag:*`, `dbt test --select tag:*`.
  - **Input**: Expects raw tables in catalog/schema (source_schema from dbt profile / bundle env).
  - **Output**: Bronze/silver/gold in e.g. `healthcare_medallion_dev_*` schemas.

There is **no task dependency** in DAB: medallion job does not depend on generator job. In production, raw tables are assumed to exist (either from a prior generator run or from another process).

### 2.2 Recommendation engine

- **Code**: `use_cases/recommendation_engine/` — `run_reco.py` (main), `config.get_config()`, `data_loading.load_reco_data()`, models (item_similarity, collaborative_filtering, hybrid_ranker), evaluation.
- **Config**: `RECO_DATA_SOURCE` (local | catalog | auto), `LOCAL_DATA_PATH`, `RECO_CATALOG_SCHEMA`; on Databricks, auto → catalog.
- **Data needs**: silver_reco_interactions, silver_products, (optional) silver_orders, gold training base — all from healthcare medallion.
- **Local**: `make reco-data` (alias data-local-generate-quick), `make reco-run` (run_reco.py with local CSV).
- **Remote**: No Databricks job defined in repo; would run by pointing a job at `run_reco.py` and setting env (e.g. RECO_CATALOG_SCHEMA).

### 2.3 Inventory optimisation

- **Code**: `use_cases/inventory_optimization/` — `run_inventory.py` (main), `config.get_config()`, plus jobs: demand_forecasting, writeoff_risk_model, replenishment_optimization.
- **Config**: `INVENTORY_DATA_SOURCE`, `LOCAL_DATA_PATH`, `INVENTORY_CATALOG_SCHEMA`; same auto → catalog on Databricks.
- **Data needs**: silver/gold from healthcare medallion (inventory, expiry_batches, writeoff_events, purchase_orders, supplier_performance, products, etc.).
- **Local**: `make inventory-data`, `make inventory-run`.
- **Remote**: No Databricks job defined in repo.

---

## 3. Integration options

### Option A: Single “EBOS data & ML” jobs bundle

One bundle that includes:
- **Tasks/jobs**: (1) Generate healthcare data → (2) Run dbt medallion → (3) Run recommendation engine → (4) Run inventory optimisation (or 3 and 4 as separate tasks/jobs in same bundle).
- **Variables**: `catalog`, `source_schema` (raw), `medallion_schema` (bronze/silver/gold), so generator writes to `{catalog}.{source_schema}`, dbt reads source_schema and writes to medallion_schema, reco/inventory set RECO_CATALOG_SCHEMA / INVENTORY_CATALOG_SCHEMA from variables.
- **Sync**: `data/healthcare_data_generator`, `data/healthcare_data_medallion`, `use_cases/` (or whole repo).
- **Pros**: One deploy, one place for targets/variables; clear pipeline order if we use task dependencies.
- **Cons**: Mixes data and ML in one bundle; larger and noisier than current small bundles.

### Option B: Four separate bundles, each co-located with its code (chosen)

- **Data generation**: `data/healthcare_data_generator/` — keep existing bundle; add 3-env targets (dev-sp, test-sp, prod-sp) and variables (catalog, source_schema).
- **Medallion**: `data/healthcare_data_medallion/` — keep existing bundle; add 3-env targets and variables (catalog, source_schema, medallion_schema_prefix).
- **Recommendation engine**: `use_cases/recommendation_engine/` — **new** `databricks.yml` and `resources/` in this folder; job runs `run_reco.py`; variables (catalog, medallion_schema) → RECO_CATALOG_SCHEMA; sync paths relative to this dir (e.g. `..` so use_cases is available).
- **Inventory optimization**: `use_cases/inventory_optimization/` — **new** `databricks.yml` and `resources/` in this folder; job runs `run_inventory.py`; variables (catalog, medallion_schema) → INVENTORY_CATALOG_SCHEMA; same sync pattern.
- **3-env targets** in every bundle: dev-sp, test-sp, prod-sp (from example_bundles/jobs): workspace host, root_path `.../.bundle/${bundle.name}/${bundle.target}`, mode (development vs production), run_as service_principal_name where applicable.
- No DAB task dependency between bundles; schedule or trigger jobs independently (medallion before reco/inventory by convention or external orchestration).



---

## 4. Scoped dev plan (Option B: four bundles, 3-env targets)

### 4.0 3-env target template (from example_bundles/jobs)

Every bundle uses three targets: **dev-sp**, **test-sp**, **prod-sp** (see `example_bundles/jobs/databricks.yml`). Each target defines: `workspace.host`, `workspace.root_path` (e.g. `/Workspace/Users/<user_or_sp>/.bundle/${bundle.name}/${bundle.target}`), `variables` (catalog, schema overrides per env), `mode` (development vs production), `run_as.service_principal_name` where applicable. Optionally override `resources.jobs.<name>.schedule.pause_status` (PAUSED in dev/test). Copy the targets block from the example and trim variables to what each bundle needs.

### 4.1 Phase 1: Data bundles — 3-env targets and variables

- **Generator** (`data/healthcare_data_generator/`): Replace current dev/prod targets with **dev-sp, test-sp, prod-sp**; add variables `catalog`, `source_schema`; ensure `generate_catalog_data_static.py` reads from env and writes to `{catalog}.{source_schema}.healthcare_*`.
- **Medallion** (`data/healthcare_data_medallion/`): Same 3-env targets; add variables `catalog`, `source_schema`, `medallion_schema_prefix`; wire dbt profile/project to use them.
- **Doc**: Update DATA_GENERATOR_DEV_PLAN.md / data/README.md to state that catalog/schema come from bundle variables.

### 4.2 Phase 2: Recommendation engine bundle (co-located)

- **Location**: `use_cases/recommendation_engine/` — add `databricks.yml` and `resources/` here.
- **databricks.yml**: bundle name (e.g. recommendation_engine), include `resources/*.yml`, variables (catalog, medallion_schema), **targets: dev-sp, test-sp, prod-sp** (same pattern as 4.0), sync paths (e.g. `..` so this directory is synced and `run_reco.py` is in workspace).
- **resources/reco_job.yml**: one job, spark_python_task or python_task pointing at `run_reco.py`; env: RECO_DATA_SOURCE=auto, RECO_CATALOG_SCHEMA from variables; job_clusters or existing cluster; environment with deps from requirements.txt.
- **Sync**: e.g. `sync.paths: [..]` so the recommendation_engine directory is the job working context; ensure Python can resolve imports (PYTHONPATH or install as package).

### 4.3 Phase 3: Inventory optimization bundle (co-located)

- **Location**: `use_cases/inventory_optimization/` — add `databricks.yml` and `resources/` here.
- **databricks.yml**: bundle name (e.g. inventory_optimization), include resources, variables (catalog, medallion_schema), **targets: dev-sp, test-sp, prod-sp**, sync paths (e.g. `..`).
- **resources/inventory_job.yml**: job running `run_inventory.py`; env: INVENTORY_DATA_SOURCE=auto, INVENTORY_CATALOG_SCHEMA from variables; same cluster/environment pattern as reco.
- Optional: separate job YAMLs for writeoff_risk, demand_forecasting, replenishment if we want different schedules.

### 4.4 Phase 4: Job entrypoints and config

- **Reco**: Already has `run_reco.main()`; on Databricks, RECO_DATA_SOURCE=auto → catalog. Job only needs to set RECO_CATALOG_SCHEMA (and optionally LOCAL_DATA_PATH if we ever want to point at workspace files). No code change if config is env-driven.
- **Inventory**: Same for `run_inventory.main()` and INVENTORY_CATALOG_SCHEMA. Ensure run_inventory.py and sub-jobs (writeoff, demand, replenishment) all use config.get_config() so they respect bundle-set env.
- **Makefile**: No change for local; `make reco-run` and `make inventory-run` stay as-is. Optional: add `make reco-deploy` / `make inventory-deploy` that run `databricks bundle deploy -t dev-sp` from `use_cases/recommendation_engine/` and `use_cases/inventory_optimization/` respectively.

### 4.5 Phase 5: Medallion → use case schema contract

- Document the **exact table names** reco and inventory expect in the medallion (e.g. silver_reco_interactions, silver_products, silver_inventory, silver_expiry_batches, …). Already implied by RECO_DEV_PLAN.md and config; add a short “Medallion tables consumed” section to BUNDLE_INTEGRATION_DEV_PLAN or to each use case’s README.
- Ensure healthcare_data_medallion dbt project builds those silver/gold models so that after `dbt run`, RECO_CATALOG_SCHEMA and INVENTORY_CATALOG_SCHEMA point at a schema that contains them.

### 4.6 Phase 6: Optional — pipeline job with dependencies

- Add an orchestration job (e.g. in one bundle or a small pipeline bundle) with tasks: (1) trigger or run medallion (e.g. run job healthcare_data_medallion_job or run dbt), (2) run_reco, (3) run_inventory, with (2) and (3) depending on (1). This gives a one-click refresh-data-and-run-ML flow for dev/demos.

---

## 5. File and directory layout (target)

```
databricks-misc/
├── data/
│   ├── healthcare_data_generator/     # bundle 1: data generation (3-env targets)
│   │   ├── databricks.yml
│   │   └── resources/
│   └── healthcare_data_medallion/     # bundle 2: medallion (3-env targets)
│       ├── databricks.yml
│       └── resources/
├── use_cases/
│   ├── recommendation_engine/         # bundle 3: reco (databricks.yml + resources/ co-located)
│   │   ├── databricks.yml
│   │   ├── resources/
│   │   │   └── reco_job.yml
│   │   ├── run_reco.py
│   │   └── ...
│   └── inventory_optimization/        # bundle 4: inventory (databricks.yml + resources/ co-located)
│       ├── databricks.yml
│       ├── resources/
│       │   └── inventory_job.yml
│       ├── run_inventory.py
│       └── ...
├── example_bundles/                   # reference only (3-env targets pattern)
└── docs/
    ├── DATA_GENERATOR_DEV_PLAN.md
    └── BUNDLE_INTEGRATION_DEV_PLAN.md # this file
```

---

## 6. Summary

| Component | Current | After integration (Option B) |
|-----------|---------|------------------------------|
| Data generator | Bundle + job; writes to UC | Same; 3-env targets (dev-sp, test-sp, prod-sp); vars catalog, source_schema |
| Medallion | Bundle + job; dbt bronze→silver→gold | Same; 3-env targets; vars catalog, source_schema, medallion_schema_prefix |
| Recommendation engine | run_reco.py; local make; no DAB job | Bundle co-located in `use_cases/recommendation_engine/`; job + 3-env targets; RECO_CATALOG_SCHEMA from var |
| Inventory optimization | run_inventory.py; local make; no DAB job | Bundle co-located in `use_cases/inventory_optimization/`; job + 3-env targets; INVENTORY_CATALOG_SCHEMA from var |
| Local dev | make data-local-*, reco-*, inventory-* | Unchanged |

**Next steps**: (1) Add 3-env targets and variables to generator and medallion bundles. (2) Add `databricks.yml` and `resources/reco_job.yml` under `use_cases/recommendation_engine/`. (3) Add `databricks.yml` and `resources/inventory_job.yml` under `use_cases/inventory_optimization/`. (4) Deploy each bundle with `databricks bundle deploy -t dev-sp` from its directory. (5) Optionally add a pipeline job that runs medallion then reco then inventory with task dependencies.
