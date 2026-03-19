---
applyTo: '**'
---

**Authoritative rules:** [`.cursor/rules/project-rules.mdc`](../../.cursor/rules/project-rules.mdc). When updating project conventions, edit that file first, then replace the markdown body below (from `### Project Overview` through `### Misc`) with the contents of that file after its YAML frontmatter.

### Project Overview
- Purpose: Implements the **EBOS AI/ML Use Cases** (see docs/EBOS_USE_CASES.md and README.md). Use-cases for healthcare/pharmaceutical distribution on Databricks + Unity Catalog (equal priority).
- Target Domain: EBOS-style supply chain, logistics, healthcare analytics (recommendation engine, inventory optimisation, document intelligence, customer service agents, insights & analytics).
- Platform: Databricks (host configured per target in bundle `databricks.yml`)
- Scope: Shared data foundation (extend healthcare_data_generator/medallion for reuse) plus use-cases under use_cases/<name>/; each use-case has its own DAB bundle where needed.

### Repo Structure
- **data/** — Shared data foundation. Generators (healthcare, prescription PDFs) and medallion. Extended incrementally for use-cases; one medallion, n use-cases on top.
- **use_cases/** — One subdirectory per EBOS use-case (recommendation_engine, demand_forecasting, inventory_optimization, document_intelligence, customer_service_agent, ranging_consolidation, market_intelligence, franchise_analytics).
- **bundles/** — Shared DAB packs not scoped to a single `use_cases/<name>/` tree (e.g. `bundles/uc_foundation` for Unity Catalog schemas/volumes and related jobs).
- **docs/** — EBOS_USE_CASES.md (use-cases spec), MODELLING_OPTIONS.md (alternative / non-EBOS options), LUNCH_AND_LEARN.md (session plan; to be aligned with EBOS).

### Databricks Bundles (multi-DAB pattern)
- **General pattern**: All Databricks Asset Bundles (DABs) for a component live under a `bundles/` subdirectory, and each bundle keeps its own `resources/` folder alongside its `databricks.yml`, mirroring `example_bundles`.
- **Use-case bundles** (`use_cases/<name>/bundles/`):
  - `bundles/job/databricks.yml` — primary **jobs bundle** for the use-case (training, batch scoring, orchestration). This bundle should:
    - keep job resources under `use_cases/<name>/bundles/job/resources/*.yml`
    - `include: resources/*.yml` (relative to the bundle directory).
    - define `sync.paths` (typically repo root) so `use_cases/` and `data/` code is available in the workspace.
    - declare shared `variables` (e.g. catalog, medallion_schema, workspace_root).
    - define 3‑env `targets` (`dev-sp`, `test-sp`, `prod-sp`) with `workspace.host`, `workspace.root_path`, per-target `variables` overrides, and optional `resources.jobs.*.schedule.pause_status` plus `run_as.service_principal_name`.
  - `bundles/serving/databricks.yml` — optional **endpoints bundle** for model-serving endpoints (per use-case):
    - keep endpoint resources under `use_cases/<name>/bundles/serving/resources/*.yml`
    - `include: resources/*.yml`.
  - `bundles/app/databricks.yml` — optional **apps/interactive bundle** (e.g. Streamlit Databricks Apps) for demos/ops UIs:
    - keep app resources under `use_cases/<name>/bundles/app/resources/*.yml`
    - `include: resources/*.yml`.
- **Data bundles** (`data/<component>/bundles/databricks.yml`, same shape as use-case bundles):
  - `include: resources/*.yml` with job resources in `data/<component>/bundles/resources/*.yml`; `sync.paths` to repo root (`../../..` from `bundles/`).
  - `data/healthcare_data_generator/bundles/databricks.yml` — generator jobs for raw synthetic data.
  - `data/healthcare_data_medallion/bundles/databricks.yml` — dbt medallion bundle (bronze/silver/gold).
- **Example bundle structure (reference only)**:
  - `example_bundles/jobs/databricks.yml` demonstrates the canonical **jobs** bundle shape:
    - `bundle`: name/uuid
    - `include: resources/*.yml` — all jobs for that bundle live under a sibling `resources/` directory (e.g. `example_bundles/jobs/resources/*.yml`).
    - `sync.paths` — which source dirs to sync into the workspace (e.g. `../../notebooks`, `../../src`).
    - `variables` — env-specific settings (catalog, schema, service principal, secrets, endpoint scaling, etc.).
    - `targets dev-sp/test-sp/prod-sp` — each with `workspace.host`, `workspace.root_path`, `variables` overrides, and optional `resources.jobs.*.schedule.pause_status` and `run_as.service_principal_name`.
  - `example_bundles/endpoints/databricks.yml` shows the same pattern for endpoints bundles.
  - Real use-case bundles (e.g. `use_cases/recommendation_engine/bundles/{job,serving,app}/databricks.yml`, `use_cases/inventory_optimization/bundles/job/databricks.yml`) should follow this structure: bundle metadata, local `resources/*.yml` next to each bundle file, repo-root `sync.paths`, shared `variables`, and 3‑env `targets` (dev-sp/test-sp-prod-sp).
- **Bundle lifecycle (deploy vs destroy)**:
  - **`databricks bundle deploy`** (and removing resources from YAML then deploying again) is the normal way to reconcile workspace state with config; orphaned resources defined only in prior deploys can be removed on deploy depending on bundle state.
  - **`databricks bundle destroy`** removes resources previously deployed for this bundle’s identity (bundle name + **target** + workspace). Use for explicit teardown, env reset, or CI cleanup. **Irreversible** for those resources; the CLI prompts by default.
  - In YAML, **`lifecycle`** on a resource can prevent it from being destroyed when running `bundle destroy` (see Databricks bundle docs: resources → lifecycle).
- **Makefile DAB commands (always run from repo root)** — thin wrappers around the Databricks CLI so CI and humans share the same `BUNDLE=` names and targets:
  - **`make dab-list`** — valid `BUNDLE=` values for the generic targets below.
  - **`make dab-validate` / `dab-deploy` / `dab-run` / `dab-destroy`** — require `BUNDLE=<name>`; optional **`DAB_TARGET`** (default `dev-sp`), **`DAB_PROFILE`** (defaults to `DAB_TARGET`). See **`make help`** for use-case shortcuts (`reco-dab-deploy`, `doc-intel-dab-destroy`, `foundation-dab-destroy-uc`, etc.).
  - **`make dab-destroy`** — runs `databricks bundle destroy` from the mapped bundle directory. For non-interactive runs (e.g. CI), set **`DAB_DESTROY_AUTO_APPROVE=1`** to pass **`--auto-approve`**.
  - **`DATABRICKS_BUNDLE_ENGINE=direct`** — the Makefile forces this for **`uc_foundation`** and **`ai_powered_insights_genie_spaces`** on validate / deploy / **destroy**, matching deploy requirements for those resources.
  - **Multi-bundle use-cases** (reco, doc-intel, ai-insights) expose destroy shortcuts that run **`dab-destroy`** per bundle in **reverse dependency order** (e.g. app → serving → jobs) so dependents are torn down first.

### Databricks Apps (Streamlit)
- We standardise on **Streamlit** for Databricks Apps.
- Per use-case, app code lives under `use_cases/<name>/app/`:
  - `app/app.py` — main Streamlit entrypoint (also used for local `streamlit run app.py`).
  - `app/requirements.txt` — app-only dependencies (Streamlit, SQL connector, requests, plotting, etc.).
- The **apps bundle** is `use_cases/<name>/bundles/app/databricks.yml` and includes `bundles/app/resources/*.yml`.
- App resources define a single Streamlit app pointing at the code directory:
  - `source_code_path: use_cases/<name>/app`
  - `environment.spec.dependencies` should normally reference the requirements file (e.g. `- -r use_cases/<name>/app/requirements.txt`) rather than duplicating libraries inline.
- Local dev pattern for any app:
  - **Preferred:** `make <use-case>-app-run` from **repo root** — uses `.streamlit/config.toml` + `STREAMLIT_LOCAL_OPTS` (`runOnSave`, file watcher) so saves rerun without a prompt and imports under `use_cases/` are watched.
  - **From app dir:** `cd use_cases/<name>/app && uv pip install -r requirements.txt && streamlit run app.py --server.runOnSave true` (watcher only covers that subtree; use root-based runs to pick up shared modules).

### Job taxonomy (retrain vs apply)
- For ML-heavy use-cases (e.g. recommendation, inventory optimisation), split jobs into **types** and then fan out by **model**:
  - **Retrain jobs**: retrain or recompute model state / policy (e.g. demand forecasting models, write-off risk classifier, replenishment ROP policy). These:
    - live in a dedicated resource file such as `bundles/job/resources/retrain_jobs.yml`
    - have one job per model subtype (e.g. `*_demand_forecasting_retrain`, `*_writeoff_risk_retrain`, `*_replenishment_retrain`)
    - typically use a heavier environment (MLflow, Prophet, XGBoost, statsmodels, etc.).
  - **Batch apply jobs**: apply the latest trained models/policies to gold tables (e.g. `gold_demand_forecast`, `gold_writeoff_risk_scores`, `gold_replenishment_recommendations`). These:
    - live in a separate resource file such as `bundles/job/resources/batch_apply_jobs.yml`
    - also have one job per model subtype (e.g. `*_demand_forecasting_apply`, `*_writeoff_risk_apply`, `*_replenishment_apply`)
    - can use a leaner environment focused on reading medallion tables and writing gold outputs.
- It is acceptable (and often convenient) for retrain and apply jobs to reuse the same Python entrypoints initially; over time, you can split `*_retrain.py` vs `*_apply.py` while keeping the DAB job taxonomy unchanged.

### Per-model modules under `models/`
- For each model **within a use-case** (e.g. `item_similarity`, `als`, `hybrid_ranker` in `recommendation_engine`; `demand_forecasting`, `writeoff_risk`, `replenishment` in `inventory_optimization`), group **all model-specific code** under `use_cases/<name>/models/<model_name>/`:
  - `use_cases/<name>/models/<model_name>/core.py` — core model logic (train-time utilities, scoring helpers, wrappers around libraries like LightGBM, implicit, statsmodels, Prophet, XGBoost, etc.).
  - `use_cases/<name>/models/<model_name>/train.py` — orchestration entrypoint for training / policy recompute:
    - uses `config.get_config()` and existing data loaders (`data_loading` modules),
    - calls into `<model_name>.core` functions,
    - handles MLflow setup and logging when appropriate.
  - `use_cases/<name>/models/<model_name>/predict.py` — orchestration entrypoint for batch apply / scoring:
    - loads models from MLflow (or uses pure policy functions in `core.py`): **local** = local model URI (env e.g. `*_MODEL_URI`: `runs:/...` or `file:///...`); **Databricks** = registry/model URI from env or job config,
    - loads input data via use-case config and data loaders: **local** = DuckDB medallion (when `DBT_DUCKDB_PATH` and tables exist) with CSV fallback; **Databricks** = Unity Catalog,
    - writes results to local artifacts (DataFrame / CSV) or Unity Catalog tables when running on Databricks.
- Existing flat model modules at the use-case root (e.g. `use_cases/recommendation_engine/item_similarity.py`, `collaborative_filtering.py`, `hybrid_ranker.py`, `use_cases/inventory_optimization/demand_forecasting.py`, `writeoff_risk_classifier.py`, `replenishment_optimizer.py`) should be **gradually refactored** so that:
  - Their substantive contents move into the corresponding `models/<model_name>/core.py`.
  - All referenced imports/callsites are updated to point at the new `models/<model_name>/...` locations, and the old modules are removed once nothing references them (avoid shim re-exports).
- New model work should be added under `models/<model_name>/` from the start (core + train/apply), and other modules should import from there using root-based imports.

### Naming: DAB config vs Python code
- Reserve the `bundles/**` tree strictly for **DAB configuration** (bundle `databricks.yml` files and their `resources/*.yml` job/endpoint/app definitions).
- Keep substantive Python entrypoints / job scripts outside `bundles/`, under clear code-centric names such as:
  - `use_cases/<name>/run_<use_case>.py` for the main pipeline entrypoint.
  - `use_cases/<name>/pipelines/` or `use_cases/<name>/job_scripts/` for per-step Python scripts that DAB jobs call.
- Do **not** put Python scripts under `bundles/` or name code folders `resources/` — that name is reserved for bundle YAML resources in the DAB layer.

### Technical Architecture
- Development Model: Local development with Databricks Connect for remote execution
  - Local Python: UV env `.venv` at repo root — **`make uv-setup`** (one command) or `make uv-venv && make install`; **`make install` always includes the `dev` extra** (formatters, pytest). **`make venv-clean`** removes `.venv`. Repo root is the source root: use imports from root (e.g. `from data.prescription_pdf_generator...`, `from use_cases...`). No per-subproject PYTHONPATH; set PYTHONPATH to repo root only if not using the venv.
- Local vs remote: Use `utils.env_utils.is_running_on_databricks()` to fork behaviour. When local (no Databricks runtime): load data from `data/local/` CSVs or env `LOCAL_DATA_PATH`; skip Spark where applicable. MLflow uses local `./mlruns` when not on Databricks. See docs/EBOS_USE_CASES.md (Development Patterns).
- **Local medallion (faster dev)**: Replicate the medallion as completely and realistically as possible locally to speed up development (run dbt without Databricks). Use a local DB as the dbt target: **prefer DuckDB** (dbt-duckdb) for closest realism—analytical SQL, optional CSV-as-source, single file. SQLite (dbt-sqlite) is fine if you prefer; populate from CSVs first. Production keeps the Databricks profile.
- **Environment switching for prediction (batch apply)**: When running **locally**, prediction/apply scripts must honour the same environment split as training:
  - **Model loading**: Use a **local model URI**—e.g. MLflow `runs:/<run_id>/model` or `file:///path/to/artifact`—configured via use-case or model-specific env (e.g. `WRITEOFF_RISK_MODEL_URI`, `*_MODEL_URI`). Do not assume a registry model (e.g. `models:/.../Production`) exists locally unless that URI is explicitly set; on Databricks, jobs can set the env to a registry URI.
  - **Data loading**: Prefer loading input data from the **local DuckDB medallion** when available: use `DBT_DUCKDB_PATH` (default e.g. `data/local/medallion.duckdb`) and read from the same silver/gold table names as in catalog (e.g. `silver_inventory`, `silver_orders`). If the DuckDB file or medallion tables are not present, **fall back** to CSV from `data/local` (or `LOCAL_DATA_PATH` / use-case config) so that local dev works with either "DuckDB medallion" or "CSV only". Config (e.g. `get_config()`) should support this by exposing a local data source that can be "duckdb" (medallion) or "csv" (raw CSVs), with duckdb preferred when the file and tables exist.
  - This keeps parity with production: production = Unity Catalog + registry/model URIs; local = DuckDB medallion (preferred) or CSV + local MLflow runs or file URIs.
- Data Governance: Unity Catalog with three-level namespace (catalog.schema.table)
  - currently using the `workspace.default` catalog/schema

### Code/Infrastructure Guidelines
- File Organization: Use flat structures where possible for Databricks compatibility
- Development Workflow: Local development → Databricks Connect → remote execution, generally assume we're running remotely unless otherwise specified
- Python Version: Ensure alignment between local and remote environments (noted as potential challenge)
- Performance: Databricks Connect is slower but more convenient than git-based workflows

### Data & ML Patterns
- Tree-based Methods: XGBoost/LightGBM for tabular operations data
- Time Series: Prophet, ARIMA, LSTM, Temporal Fusion Transformers for forecasting
- NLP: Transformers for document processing, call summarization
- **Feature engineering:** Keep in dbt only base, reusable aggregates (feature storage / wide tables). Keep model-specific features and serving logic in Python (same code path as training) to avoid train–serve skew; read from gold/silver in ML code.

### Code Standards
- use KISS principles - keep it simple, stupid, we prefer straight forward/direct implementations that prioritize clarity over complexity
  - do not use `__init__.py` files unless absolutely necessary
- use DRY principles - don't repeat yourself, we prefer to reuse code/functions/classes/modules/etc. instead of duplicating code/functions/classes/modules/etc.
- if possible, use functions/functional programming instead of classes/object-oriented programming
- Logging: Always use loguru instead of print statements
- Module Structure: Prefer semantic naming (parent_module.semantic_name) over verbose names
- Imports: Always use **root-based imports** from the repo root (e.g. `from use_cases.inventory_optimization.demand_forecasting import prepare_forecasting_data, run_xgboost_experiment`, `from data.healthcare_data_generator.src.healthcare_data_generator import ...`). Avoid relative or package-local imports (`from .foo import ...`, `from foo import ...` inside subpackages) so that scripts run consistently from the repo root, Databricks jobs, and DAB bundles.
- Refactors: if you change/refactor a module’s location, propagate that change by updating all referenced imports/call-sites; avoid shim/re-export modules for the rename.

### Misc
- Do not create unnecessary markdown/README files; we typically just one one root level README and then perhaps one in a major module ONLY if the complexity warrants it
