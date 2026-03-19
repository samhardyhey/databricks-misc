# Unity Catalog organisation: implementation plan

## Purpose

This document is the **source of truth** for how we organise Unity Catalog (UC) objects (catalogs, schemas, volumes) across the repo, and the phased plan to migrate existing use-cases to the target layout.

Goals:

- Keep a **shared, env-isolated foundation** (raw generator + dbt medallion) that is reusable across all use-cases.
- Ensure every use-case writes **owned outputs** (features, predictions, recommendations, marts) into **use-case-scoped schemas** (and volumes where needed).
- Ensure **dev/test/prod isolation**, especially for managed volumes (no shared paths across environments).
- Keep the **medallion clean and use-case agnostic**, pushing use-case-specific transformations into the use-case bundle/pipeline.

Non-goals:

- Introducing multiple catalogs is optional and not required for the initial migration (we are currently standardised on a single catalog).

---

## Target UC layout (end state)

### Catalog

- **Short term**: one catalog (default: `workspace`).
- **Long term (optional)**: introduce a dedicated catalog (e.g. `ebos`) if/when we have metastore privileges and want stronger governance boundaries.

### Shared platform schemas (per environment)

These are created/owned by the **platform foundation** (generator + dbt medallion).

- **Raw generator outputs**:
  - `workspace.healthcare_dev_raw`
  - `workspace.healthcare_test_raw`
  - `workspace.healthcare_prod_raw`

- **Medallion (dbt) outputs** (layer-separated):
  - `workspace.healthcare_medallion_dev_bronze`
  - `workspace.healthcare_medallion_dev_silver`
  - `workspace.healthcare_medallion_dev_gold`
  - (and similarly for `test` and `prod`)

Guideline: these schemas should remain **use-case agnostic**, containing broadly reusable curated tables and standard aggregates.

### Use-case schemas (per environment)

Each use-case has a dedicated schema for its owned outputs:

- `workspace.recommendation_engine_dev`
- `workspace.inventory_optimization_dev`
- `workspace.ai_powered_insights_dev`
- `workspace.document_intelligence_dev`
- (and similarly for `test` and `prod`)

Rule: **use-case code must never write into medallion schemas**. Use-cases only **read** shared medallion tables and **write** to their own schema.

### Volumes (per environment, per use-case)

Volumes live under `(catalog, schema, volume)` and are accessed at:

- `/Volumes/<catalog>/<schema>/<volume>`

Document intelligence requires env-scoped volumes to avoid cross-environment mixing:

- dev: `/Volumes/workspace/document_intelligence_dev/prescription_documents`
- test: `/Volumes/workspace/document_intelligence_test/prescription_documents`
- prod: `/Volumes/workspace/document_intelligence_prod/prescription_documents`

---

## Foundation provisioning (DAB)

### Single “first-class” foundation bundle

All UC schemas/volumes required by every other bundle are provisioned by:

- `bundles/uc_foundation/`

This bundle is deployed **before** any generator/medallion/use-case bundles.

Notes:

- Catalog creation via DAB requires the **direct deployment engine** (Databricks CLI guidance). We currently keep catalog fixed and focus on schemas/volumes.
- The repo provides a convenience command:
  - `make uc-foundation-deploy`
  - override target: `make uc-foundation-deploy UC_FOUNDATION_TARGET=test-sp`

---

## Data flow contract (what lives where)

### Platform pipelines (shared)

1) **Healthcare generator** writes raw tables into `healthcare_<env>_raw`.
2) **dbt medallion** reads raw and writes curated tables into `healthcare_medallion_<env>_{bronze|silver|gold}`.

### Use-case pipelines (owned)

Each use-case:

- **Reads** from shared medallion silver/gold (and optionally raw if needed for backfills).
- **Writes** all derived artifacts into its use-case schema:
  - use-case-specific feature tables
  - training datasets (if persisted)
  - inference outputs / recommendations / scores
  - evaluation tables
  - BI-ready marts (if not part of the shared medallion)

This keeps the medallion clean and avoids coupling use-cases via “shared but use-case-flavoured” gold tables.

---

## Configuration pattern: input vs output namespaces

To enforce “shared inputs, use-case outputs”, each use-case should have **two** configurable namespaces:

- **Input namespace**: shared medallion schema(s) (env-specific).
- **Output namespace**: use-case schema (env-specific).

Implementation principle:

- Reads use the medallion namespace(s).
- Writes use the use-case namespace.

This avoids duplicating medallion tables into each use-case schema.

---

## Local vs remote development

- **Local**: Data source is `local` (CSV or DuckDB medallion). No Unity Catalog schema env vars are required. Use-case config exposes `duckdb_path`, `duckdb_medallion_schema`, and leaves `input_*` / `output_schema` unset (or empty). Train/apply code reads from local files or DuckDB and writes to local artifacts (e.g. CSV, MLflow local).
- **Remote (Databricks)**: Data source is `catalog`. Jobs set `*_INPUT_*_SCHEMA` and `*_OUTPUT_SCHEMA` (e.g. `RECO_INPUT_SILVER_SCHEMA`, `RECO_OUTPUT_SCHEMA`). Code reads from shared medallion schemas and writes to use-case schemas (and UC volumes where applicable).
- **dbt medallion**: When run on Databricks, the dbt profile uses a base schema (e.g. `healthcare_medallion_dev`). Model config uses `+schema: bronze | silver | gold`. dbt’s default `generate_schema_name` produces layer schemas `healthcare_medallion_<env>_bronze`, `_silver`, `_gold`, so no dbt change is needed for the layer-schema standard.

---

## Phased migration plan

### Phase 0 — Inventory & mapping (prepare)

Deliverables:

- For each use-case, list:
  - **Inputs** read from medallion (tables + schemas).
  - **Outputs** currently written (tables + schemas).
  - Ownership decision: which outputs belong in medallion vs use-case schema (default: use-case schema).

### Phase 1 — Foundation provisioning (schemas + volumes) — Done

Deliverables:

- `uc_foundation` provisions:
  - shared raw + medallion schemas (all envs), including layer schemas `healthcare_medallion_<env>_{bronze,silver,gold}`
  - use-case output schemas (all envs)
  - doc-intelligence env-scoped schemas + volumes

### Phase 2 — Document intelligence isolation (high priority) — Done

Deliverables:

- Doc-intel tables always live in `workspace.document_intelligence_<env>`.
- Doc-intel PDFs always live in `/Volumes/workspace/document_intelligence_<env>/prescription_documents`.
- No dev/test/prod mixing for doc-intel volumes.

### Phase 3 — Reco outputs → reco schema; Inventory outputs → inventory schema — Done

Deliverables:

- Reco:
  - reads medallion silver/gold from shared schemas (`RECO_INPUT_SILVER_SCHEMA`, `RECO_INPUT_GOLD_SCHEMA`)
  - writes all candidate/reco output tables to `workspace.recommendation_engine_<env>` (`RECO_OUTPUT_SCHEMA`)
- Inventory:
  - reads medallion silver/bronze/gold from shared schemas (`INVENTORY_INPUT_*_SCHEMA`)
  - writes all scoring/recommendation outputs to `workspace.inventory_optimization_<env>` (`INVENTORY_OUTPUT_SCHEMA`)

### Phase 4 — Move use-case-flavoured “gold” out of shared medallion

Deliverables (incremental):

- Keep shared medallion gold limited to broadly reusable datasets.
- Move use-case-specific feature/training base tables into the owning use-case schema.

**Encoding use-case-owned transforms:** Each moved transform is explicitly implemented in the use-case and runnable both locally and remotely:

- **Pipeline script** in `use_cases/<uc>/pipelines/` (e.g. `build_training_base.py`) that reads from medallion (or local DuckDB/CSV) and writes to output_schema (catalog) or a local path (e.g. `data/local/<uc>/…`).
- **Make target** (e.g. `make reco-build-training-base`) to run the transform locally.
- **DAB job** in the use-case job bundle (e.g. `recommendation_engine_build_training_base`) so the transform runs on a schedule or as a dependency before retrain.

Downstream code (e.g. data_loading, train scripts) reads these tables from the use-case output schema (catalog) or the local path (local), not from the medallion.

**Phase 4 status**

- **Reco (done):** `gold_reco_training_base` and `gold_reco_candidates` removed from medallion. Reco owns the training-base transform via `pipelines/build_training_base.py`, `make reco-build-training-base`, and DAB job `recommendation_engine_build_training_base`. Training reads from `output_schema.gold_reco_training_base` (catalog) or local parquet (local).
- **Inventory:** No inventory-specific gold tables exist in the medallion. Inventory reads only silver/bronze and writes all outputs (e.g. `gold_writeoff_risk_scores`, `gold_replenishment_recommendations`) to `output_schema`; no Phase 4 move required.
- **Remaining medallion gold (broadly reusable):** The shared medallion keeps analytics/BI gold tables: `gold_product_performance`, `gold_pharmacy_performance`, `gold_financial_analytics`, `gold_supply_chain_performance`, `gold_ml_ready_dataset`. None are currently consumed by use-case code. If a use-case later adopts `gold_ml_ready_dataset` (or similar) as a primary input, consider moving that transform into the owning use-case as a pipeline + make + DAB.

### Phase 5 — Governance hardening (ongoing)

Deliverables:

- Grants:
  - shared medallion schemas: write for platform pipeline principal; read for consumers
  - use-case schemas: write for the use-case principal; read for intended analyst groups/apps
  - volumes: write/read scoped per env and use-case
- Minimal “data contract” docs per use-case:
  - output tables list + semantics + freshness expectations

---

## Local make targets – operational notes

- **Status:** All local e2e targets run successfully when executed **one at a time**: `data-local-e2e`, `doc-intel-local-e2e`, `reco-local-e2e`, `inventory-local-e2e`.
- **DuckDB concurrency:** `data-local-e2e`, `reco-local-e2e`, and `inventory-local-e2e` all use the same file `data/local/medallion.duckdb`. Do **not** run these in parallel (e.g. in separate terminals); DuckDB will report a lock conflict. Run them sequentially.
- **Doc-intel e2e:** By default `doc-intel-local-e2e` does not start the Streamlit app (headless). Set `DOCINT_SMOKE_RUN_STREAMLIT=1` when invoking the smoke script if you want the annotator app to launch.

---

## Checklist (repeatable per use-case)

For a given use-case `<uc>`:

- [ ] Define `<uc>_<env>` output schema.
- [ ] Identify shared medallion input tables (silver/gold/bronze as needed).
- [ ] Ensure runtime config distinguishes input namespace(s) vs output namespace; require input/output schema env vars only when `data_source == 'catalog'` (local runs use DuckDB/CSV and do not need them).
- [ ] Update bundle/job env vars so writes land in `<uc>_<env>`.
- [ ] Backfill/migrate any existing output tables from shared schemas into `<uc>_<env>`.
- [ ] Encode use-case-owned transforms as pipeline script + make target + DAB job (see Phase 4).
- [ ] Apply UC grants (least privilege).
- [ ] Update dashboards/apps to point to `<uc>_<env>` or layer medallion schemas if they consume them.

**Completed for:** recommendation_engine (output schema; gold_reco_training_base moved to pipeline + make reco-build-training-base + DAB job), inventory_optimization, document_intelligence (output schema + volume); ai_powered_insights (dashboards/genie use layer medallion vars).

