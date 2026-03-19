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

## Phased migration plan

### Phase 0 — Inventory & mapping (prepare)

Deliverables:

- For each use-case, list:
  - **Inputs** read from medallion (tables + schemas).
  - **Outputs** currently written (tables + schemas).
  - Ownership decision: which outputs belong in medallion vs use-case schema (default: use-case schema).

### Phase 1 — Foundation provisioning (schemas + volumes)

Deliverables:

- `uc_foundation` provisions:
  - shared raw + medallion schemas (all envs)
  - use-case output schemas (all envs)
  - doc-intelligence env-scoped schemas + volumes

### Phase 2 — Document intelligence isolation (high priority)

Deliverables:

- Doc-intel tables always live in `workspace.document_intelligence_<env>`.
- Doc-intel PDFs always live in `/Volumes/workspace/document_intelligence_<env>/prescription_documents`.
- No dev/test/prod mixing for doc-intel volumes.

### Phase 3 — Reco outputs → reco schema; Inventory outputs → inventory schema

Deliverables:

- Reco:
  - reads medallion silver/gold from shared schemas
  - writes all candidate/reco output tables to `workspace.recommendation_engine_<env>`
- Inventory:
  - reads medallion silver/bronze from shared schemas
  - writes all scoring/recommendation outputs to `workspace.inventory_optimization_<env>`

### Phase 4 — Move use-case-flavoured “gold” out of shared medallion

Deliverables (incremental):

- Keep shared medallion gold limited to broadly reusable datasets.
- Move use-case-specific feature/training base tables into the owning use-case schema.

Implementation options:

- dbt mini-project per use-case that reads shared medallion and writes to use-case schema; or
- Spark/Python tasks within the use-case bundle to compute and write those outputs.

### Phase 5 — Governance hardening (ongoing)

Deliverables:

- Grants:
  - shared medallion schemas: write for platform pipeline principal; read for consumers
  - use-case schemas: write for the use-case principal; read for intended analyst groups/apps
  - volumes: write/read scoped per env and use-case
- Minimal “data contract” docs per use-case:
  - output tables list + semantics + freshness expectations

---

## Checklist (repeatable per use-case)

For a given use-case `<uc>`:

- [ ] Define `<uc>_<env>` output schema.
- [ ] Identify shared medallion input tables (silver/gold).
- [ ] Ensure runtime config distinguishes input namespace(s) vs output namespace.
- [ ] Update bundle/job env vars so writes land in `<uc>_<env>`.
- [ ] Backfill/migrate any existing output tables from shared schemas into `<uc>_<env>`.
- [ ] Apply UC grants (least privilege).
- [ ] Update dashboards/apps to point to `<uc>_<env>` outputs if they consume them.

