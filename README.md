# EBOS AI/ML platform

Implements **EBOS AI/ML use-cases** for healthcare/pharmaceutical distribution on **Databricks + Unity Catalog**: one shared data foundation (generators + medallion), use-cases on top.

- **Use-case spec:** [docs/EBOS_USE_CASES.md](docs/EBOS_USE_CASES.md) — data needs, modelling, architecture, file layout per use-case.
- **Data & platform:** [docs/DATA_AND_PLATFORM.md](docs/DATA_AND_PLATFORM.md) — UC layout, data flow, grants, data contracts, generator/medallion scope, local dev.

---

## Databricks practice notes (policy development)

The **`marvelous_mlops/`** tree is an explicit **policy-development** workstream: it **ingests public MLOps / Databricks teaching material** (starting with the [Marvelous MLOps](https://medium.com/marvelous-mlops) Medium publication, plus optional Substack / YouTube) so we can **summarize and extract practical tips** that inform how we structure bundles, jobs, monitoring, and MLflow usage in this repo.

- **What it is for:** turn third-party best-practice content into concise, repo-relevant guidance—not to ship that content as product, but to keep our conventions and `.cursor` rules aligned with current Databricks patterns.
- **How to use it:** see [marvelous_mlops/README.md](marvelous_mlops/README.md). From repo root: `make marvelous-mlops-venv` (installs the `marvelous_mlops` optional extra from `pyproject.toml` into the repo `.venv`), then `make marvelous-mlops-fetch-medium` (and digest: `make marvelous-mlops-practice-digest`).
- **Ethics:** fetchers only use public feeds/pages and rate limit requests; full articles remain on the source sites.

---

## Layout & stack

- **Use-cases:** `use_cases/<name>/` (recommendation_engine, inventory_optimization, document_intelligence, ai_powered_insights, etc.); each with DAB bundles (job, serving, app) as needed.
- **Data:** `data/healthcare_data_generator/`, `data/healthcare_data_medallion/`, `data/prescription_pdf_generator/`; [data/README.md](data/README.md) for generator → medallion locally.
- **Platform:** Databricks (free edition); Unity Catalog (**demo catalog** `ebos_uc_demo` for shared multi-use-case artefacts — see [docs/DATA_AND_PLATFORM.md](docs/DATA_AND_PLATFORM.md)); dbt medallion (bronze/silver/gold); MLflow.

**Implemented:** Recommendation engine (item_similarity, ALS, LightFM, ranker); inventory optimisation (demand forecasting, write-off risk, replenishment); document intelligence (PDFs, OCR, annotator); AI insights (dashboards, Genie). Customer service agent and full insights apps in progress.

---

## Quick start

### Local — prototype & test (no Databricks required)

Use this path to exercise generators, medallion (DuckDB + dbt), and use-case Python on your machine. **Do not run local e2e targets in parallel** — they share `data/local/medallion.duckdb` and will contend on locks.

1. **Env:** Install **[uv](https://docs.astral.sh/uv/)** on your PATH (`make bootstrap-system-tools` puts it in `~/.local/bin`). Then **`make uv-setup`** (same as `make uv-venv && make install`). `install` uses **`uv sync`** only—uv-created `.venv` does not include `pip`, so do not fall back to `pip install -e .`. Optional extras: `make reco-install`, `make doc-intel-local-install`, … Remove the env with **`make venv-clean`**.
2. **Unit/smoke (pytest):** `make test`.
3. **Data foundation e2e:** `make data-local-e2e` — clean → generate CSVs → DuckDB load → `dbt run` → `dbt test`. (Incremental steps: `make data-local-generate-quick`, `make data-local-duckdb-load`, `make data-local-dbt-run`, `make data-local-dbt-test`.)
4. **Use-case e2e (after medallion exists):**
   - Recommendation: `make reco-local-e2e` (includes local data prep, training base, train/apply smoke).
   - Inventory: `make inventory-local-e2e`.
   - Document intelligence: `make doc-intel-local-install` then `make doc-intel-local-e2e` (PDF → OCR → field extraction smoke).
   - **All of the above in order:** `make use-cases-local-e2e` (includes `doc-intel-local-install` before doc-intel e2e).
5. **Streamlit demos (local only):** `make data-local-medallion-app-run` (browse DuckDB medallion tables after `make data-local-dbt-run`), plus `make reco-local-app-run`, `make doc-intel-local-app-run`, `make ai-insights-local-app-run` (AI insights router needs Genie/dashboard config to be useful).

Per-model local train/apply and other shortcuts: `make help`.

### Remote — Databricks & bundles

Running jobs, apps, and UC-backed pipelines **in a workspace** needs auth (CLI profile / SP), a provisioned catalog and schemas, warehouse IDs where applicable, and **Asset Bundle** deploys — not the local DuckDB path above. Start with [docs/DATA_AND_PLATFORM.md](docs/DATA_AND_PLATFORM.md) and [docs/EBOS_USE_CASES.md](docs/EBOS_USE_CASES.md) (*Databricks bundle prerequisites*). Typical flow: `make uc-foundation-deploy` → valid bundles (`make dab-list`, `make dab-workspace-print`, `make *-dab-deploy`). Bundle paths use `workspace_bundle_root` / `bundle_deploying_user_name` in `**/bundles/**/databricks.yml` (override with `databricks bundle deploy --var ...`).

See [Makefile](Makefile) for full targets (`make help`).
