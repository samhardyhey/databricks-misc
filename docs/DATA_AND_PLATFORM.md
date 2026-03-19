# Data & platform

Single reference for **where data lives** (Unity Catalog layout, data flow), **who can access it** (grants), **what use-cases read/write** (contracts), and **how data is produced** (generator/medallion scope, local dev). Use-case specs (modelling, apps) are in [EBOS_USE_CASES.md](EBOS_USE_CASES.md).

**Databricks Asset Bundles:** Each jobs/serving/app bundle keeps `databricks.yml` beside a **`resources/`** folder; the bundle file uses `include: resources/*.yml` so all job/endpoint/app definitions in that folder are loaded (no `../../resources/...` indirection). **Data** components use the same pattern: `data/healthcare_data_generator/bundles/{databricks.yml,resources/*.yml}` and the same for `healthcare_data_medallion`. **`workspace.root_path`** in bundle targets is set to `/Workspace/Users/sam.hardy@ebosgroup.com/.bundle/...` (repo default); change to your Databricks user if needed, or set **`WORKSPACE_USER_EMAIL`** when using Makefile helpers (`make dab-workspace-print`). Targets use **`run_as.service_principal_name`** plus **`permissions`** for `sam.hardy@ebosgroup.com` and the same SP (`CAN_MANAGE` on bundle-managed resources where the bundle API supports it). **Unity Catalog** table/volume ACLs for those principals must still be applied via grants/runbooks (`make uc-foundation-deploy`, `databricks grants`, etc.)—bundle permissions do not replace UC governance.

---

## 1. Unity Catalog layout

- **Catalog:** `ebos_uc_demo` — shared Unity Catalog for **demonstration / multi-use-case** artefacts (not per-project prod isolation). Create the catalog in the workspace if it does not exist before first deploy.
- **Shared (platform):** Raw `healthcare_<env>_raw`; medallion `healthcare_medallion_<env>_{bronze,silver,gold}`. Use-case code **never** writes here; they only read.
- **Use-case schemas:** `recommendation_engine_<env>`, `inventory_optimization_<env>`, `ai_powered_insights_<env>`, `document_intelligence_<env>`. Each use-case writes only to its own schema.
- **Volumes:** Doc-intel PDFs in `/Volumes/ebos_uc_demo/document_intelligence_<env>/prescription_documents` (env-scoped).

**Provisioning:** `bundles/uc_foundation/` creates all schemas and the doc-intel volume. Deploy first: `make uc-foundation-deploy` (override target with `UC_FOUNDATION_TARGET=test-sp`).

---

## 2. Data flow

- **Platform:** Healthcare generator → raw; dbt medallion → bronze/silver/gold.
- **Use-cases:** Read from medallion (silver/gold/bronze as needed); write all outputs (features, scores, recommendations, predictions) to their **output schema** only. Use-case-owned transforms (e.g. `gold_reco_training_base`) run as pipelines in the use-case (Make + DAB), not in the medallion.

**Config pattern:** Each use-case has **input** namespaces (medallion schemas) and **output** namespace (use-case schema). Env vars only required when `data_source == 'catalog'` (e.g. `RECO_INPUT_SILVER_SCHEMA`, `RECO_OUTPUT_SCHEMA`).

**Local vs remote:** Local = DuckDB/CSV, no UC env vars; remote = catalog, jobs set input/output schema env vars. dbt produces layer schemas (`healthcare_medallion_<env>_silver` etc.) by default.

**Job ordering (DAB):** Multi-step pipelines inside one job use task **`depends_on`** (e.g. medallion dbt bronze→silver→gold; doc-intel OCR→field extraction). **Across** jobs, ordering is mostly **staggered schedules** (e.g. `healthcare_data_medallion` before use-case retrains; `recommendation_engine_build_training_base` before per-model reco retrains). **Document intelligence** keeps **generate** and **pipeline** as **separate jobs** on purpose (upload/ingestion timing mirrors real-world variability). For hard guarantees between bundles, use a Databricks **orchestration job** / **Workflows** that triggers jobs in sequence.

---

## 3. Grants (least privilege)

| Scope | Write | Read |
|-------|--------|------|
| Medallion + raw | Platform pipeline principal (generator, dbt) | Use-case jobs, analysts, dashboards |
| Use-case schema | That use-case’s job principal | Analyst groups, apps (dashboards, Genie, Streamlit) |
| Doc-intel volume | Doc-intel job principal | Doc-intel apps; no cross-env |

**Apply via:** Databricks CLI (`databricks grants update schema ...`), Terraform, or DAB if your version supports UC schema `permissions`. Per-target variables: platform principal, use-case principals, analyst group names (align with job `run_as` where applicable).

---

## 4. Data contracts (use-case outputs)

Use-cases **read** from medallion; they **own** only the tables below (semantics + freshness).

| Use-case | Schema | Key outputs | Freshness |
|----------|--------|-------------|-----------|
| **recommendation_engine** | `recommendation_engine_<env>` | `gold_reco_training_base` (from pipeline), `gold_item_similarity_candidates`, other candidate tables | Before retrain / after apply (e.g. daily) |
| **inventory_optimization** | `inventory_optimization_<env>` | `gold_writeoff_risk_scores`, `gold_replenishment_recommendations`; (planned) `gold_demand_forecast` | After batch apply |
| **document_intelligence** | `document_intelligence_<env>` | `silver_doc_pages`, `silver_doc_fields_extracted`; volume `prescription_documents` | After OCR/field extraction; volume per upload |
| **ai_powered_insights** | `ai_powered_insights_<env>` | (None yet; dashboards read medallion) | — |

---

## 5. Generator & medallion scope

**Healthcare generator** (`data/healthcare_data_generator/`): Produces base tables (pharmacies, products, orders, inventory, supply_chain_events, etc.) and use-case-specific raw: product_interactions, substitution_events, inventory_availability (reco); expiry_batches, writeoff_events, purchase_orders, supplier_performance (inventory); warehouse_costs, competitor_*, store_sales, store_attributes, promotions (insights). Output: CSVs (local) or UC raw schema (remote).

**Healthcare medallion** (`data/healthcare_data_medallion/`): dbt bronze → silver → gold for all healthcare tables. Sources from raw; writes to `healthcare_medallion_<env>_{bronze,silver,gold}`. Shared gold stays analytics-only (e.g. gold_product_performance, gold_ml_ready_dataset); use-case-specific gold (e.g. reco training base) lives in use-case pipelines, not medallion.

**Other data:** **Customer service** (use case §3 in EBOS) is deferred—no generator/module in repo yet. Document intelligence uses the prescription PDF generator and optional UC tables/volumes; see [EBOS_USE_CASES.md](EBOS_USE_CASES.md) and `data/README.md` for layout.

**Local dev:** `make data-local-generate-quick`, `make data-local-duckdb-load`, `make data-local-dbt-run`. One DuckDB file (`data/local/medallion.duckdb`); do not run data/reco/inventory e2e in parallel (lock). Doc-intel: file-based under DOCINT_BASE_DIR.

---

## 6. Migration checklist (per use-case)

- [ ] Output schema `<uc>_<env>` defined in uc_foundation.
- [ ] Config: input vs output namespaces; schema env vars only when catalog.
- [ ] Bundle env vars so writes land in use-case schema.
- [ ] Use-case-owned transforms: pipeline script + Make + DAB job (see reco `build_training_base`).
- [ ] Grants applied (platform write, consumers read; use-case write, analysts read).
- [ ] Output tables and freshness reflected in §4 above.

**Done for:** recommendation_engine, inventory_optimization, document_intelligence, ai_powered_insights (dashboards/genie read medallion).
