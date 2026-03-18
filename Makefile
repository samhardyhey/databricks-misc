# Repo root (directory containing this Makefile). Run `make` from repo root.
REPO_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(patsubst %/,%,$(REPO_ROOT))

# Source root: repo root. All internal imports are from root (e.g. data.*, use_cases.*).
# After `make install`, the UV venv's editable install provides this; otherwise set PYTHONPATH.
export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

# Prefer venv python if .venv exists
VENV_PY := $(REPO_ROOT)/.venv/bin/python
PY ?= $(if $(wildcard $(VENV_PY)),$(VENV_PY),python3)
# dbt for local medallion (core dependency)
DBT_BIN := $(REPO_ROOT)/.venv/bin/dbt

# Local data: output dirs (data/local is gitignored)
DATA_LOCAL_DIR := $(REPO_ROOT)/data/local
MEDALLION_DIR := $(REPO_ROOT)/data/healthcare_data_medallion
# MLflow: backend/artifact from utils.mlflow (local vs Databricks); no Makefile override

# UC foundation (Unity Catalog schemas/volumes) deploy settings
UC_FOUNDATION_TARGET ?= dev-sp

# Document intelligence (prescription PDFs): local base dir
DOC_INTEL_PDF_OUTPUT := data/local/prescription_pdfs

# Marvelous MLOps: separate requirements, use sub-venv (make marvelous-mlops-venv first)
MARVELOUS_MLOPS_DIR := $(REPO_ROOT)/marvelous_mlops
MARVELOUS_PY := $(MARVELOUS_MLOPS_DIR)/.venv/bin/python

.PHONY: help cleanup clean-local-data format uc-foundation-deploy
.PHONY: dab-list dab-validate dab-deploy dab-run
.PHONY: dab-validate-recommendation_engine dab-deploy-recommendation_engine dab-run-recommendation_engine
.PHONY: dab-validate-inventory_optimization dab-deploy-inventory_optimization dab-run-inventory_optimization
.PHONY: dab-validate-document_intelligence dab-deploy-document_intelligence dab-run-document_intelligence
.PHONY: dab-validate-ai_powered_insights dab-deploy-ai_powered_insights
.PHONY: document-intelligence-install document-intelligence-generate-pdfs document-intelligence-generate-data document-intelligence-ocr document-intelligence-field-extraction document-intelligence-run document-intelligence-app-run
.PHONY: document-intelligence-smoke
.PHONY: data-local-generate data-local-generate-quick data-local-generate-pdfs data-local-duckdb-load data-local-dbt-run data-local-dbt-test
.PHONY: reco-data reco-run reco-install reco-item-sim-train reco-item-sim-apply reco-als-train reco-als-apply reco-app-run
.PHONY: ai-insights-app-run
.PHONY: inventory-data inventory-run inventory-install inventory-writeoff-train inventory-writeoff-apply inventory-demand-train inventory-demand-apply inventory-replenishment-train inventory-replenishment-apply
.PHONY: mlflow-ui mlflow-wipe
.PHONY: marvelous-mlops-venv marvelous-mlops-fetch-medium marvelous-mlops-fetch-substack marvelous-mlops-fetch-youtube
.PHONY: uv-venv uv-sync install uv-dev uv-activate

help:
	@echo "Targets:"
	@echo "  make uv-venv              - Create .venv (uses uv if available, else python3 -m venv)"
	@echo "  make uv-sync / install     - Install deps; use install then uv-dev for dev tools"
	@echo "  make reco-install          - Install reco use-case deps (implicit, lightgbm, mlflow)"
	@echo "  make inventory-install    - Install inventory use-case deps (scipy, lightgbm)"
	@echo "  make uv-dev               - Install dev deps (autoflake, isort, black)"
	@echo "  make uv-activate          - Print activate command for .venv"
	@echo "  make cleanup              - Remove __pycache__, .pyc, .pytest_cache, .coverage, etc."
	@echo "  make format [FMT_ARGS=.]  - Run autoflake, isort, black"
	@echo "  make mlflow-ui            - Start MLflow UI (utils.mlflow, local only); http://localhost:5001"
	@echo "  make mlflow-wipe          - Remove local MLflow DB and artifacts (experiments, runs, registry)"
	@echo ""
	@echo "  Local (data generation / medallion):"
	@echo "  make clean-local-data           - Remove data/local/, test_output/, doc-intel PDFs, medallion target/logs (start again)"
	@echo "  make data-local-generate        - Generate healthcare CSVs to data/local/ (default sizes)"
	@echo "  make data-local-generate-quick  - Generate healthcare CSVs to data/local/ (small sizes)"
	@echo "  make data-local-generate-pdfs   - Generate prescription PDFs (data/local/prescription_pdfs/)"
	@echo "  make data-local-duckdb-load     - Load data/local/*.csv into DuckDB as raw schema (run after generate)"
	@echo "  make data-local-dbt-run         - Load data/local into DuckDB then run medallion dbt (run data-local-generate-quick first if no CSVs)"
	@echo "  make data-local-dbt-test        - Build medallion (dbt run) then run dbt tests (referential integrity, etc.)"
	@echo ""
	@echo "  Recommendation engine (full sequence: data → train/log → apply; RECO_DATA_SOURCE=local|catalog|auto):"
	@echo "  make reco-install                  - Install reco deps (implicit, lightgbm, mlflow)"
	@echo "  make reco-data                     - Generate healthcare CSVs to data/local/ (alias for data-local-generate-quick)"
	@echo "  make reco-run                      - Full sequence: reco-data → train+log (run_reco_smoke.py) → batch apply (item_sim + ALS + LightFM)"
	@echo "  make reco-item-sim-train           - Train item-similarity model only"
	@echo "  make reco-item-sim-apply           - Apply item-similarity model (set ITEM_SIMILARITY_MODEL_URI for runs:/<run_id>/model)"
	@echo "  make reco-als-train                - Train ALS model only"
	@echo "  make reco-als-apply                - Apply ALS model (set ALS_MODEL_URI for runs:/<run_id>/model)"
	@echo "  make reco-app-run                  - Run recommendation Streamlit app locally"
	@echo "  make ai-insights-app-run           - Run AI Powered Insights (Genie + router) Streamlit app locally"
	@echo "  Inventory optimisation (full sequence: data → train+apply; INVENTORY_DATA_SOURCE=local|catalog|auto):"
	@echo "  make inventory-install             - Install inventory use-case deps (scipy, lightgbm)"
	@echo "  make inventory-data                - Generate healthcare CSVs (alias for data-local-generate-quick)"
	@echo "  make inventory-run                 - Full sequence: inventory-data → run_inventory_smoke.py (train write-off + replenishment, apply)"
	@echo "  make inventory-writeoff-train      - Train write-off risk classifier"
	@echo "  make inventory-writeoff-apply      - Apply write-off risk classifier to latest data"
	@echo "  make inventory-demand-train        - Train demand forecasting models"
	@echo "  make inventory-demand-apply        - Apply demand forecasting models to generate forecasts"
	@echo "  make inventory-replenishment-train - Train/recompute replenishment policy"
	@echo "  make inventory-replenishment-apply - Apply replenishment policy to generate recommendations"
	@echo ""
	@echo "UC foundation (Unity Catalog schemas/volumes):"
	@echo "  make uc-foundation-deploy        - Deploy bundles/uc_foundation to $(UC_FOUNDATION_TARGET)"
	@echo ""
	@echo "Databricks Asset Bundles (DAB):"
	@echo "  make dab-list                   - List available DAB bundle names"
	@echo "  make dab-validate BUNDLE=<name> DAB_TARGET=<dev-sp|test-sp|prod-sp>"
	@echo "  make dab-deploy   BUNDLE=<name> DAB_TARGET=<dev-sp|test-sp|prod-sp>"
	@echo "  make dab-run      BUNDLE=<name> RUN_JOB=<job-name> DAB_TARGET=<dev-sp|test-sp|prod-sp> (strict)"
	@echo ""
	@echo "Use-case DAB (bundle sets):"
	@echo "  Recommendation engine:"
	@echo "    make dab-validate-recommendation_engine"
	@echo "    make dab-deploy-recommendation_engine"
	@echo "    make dab-run-recommendation_engine RUN_JOB=<job-name>"
	@echo "      allowed RUN_JOB: recommendation_engine_retrain recommendation_engine_lightfm_retrain recommendation_engine_apply recommendation_engine_lightfm_apply"
	@echo "  Inventory optimisation:"
	@echo "    make dab-validate-inventory_optimization"
	@echo "    make dab-deploy-inventory_optimization"
	@echo "    make dab-run-inventory_optimization RUN_JOB=<job-name>"
	@echo "      allowed RUN_JOB: inventory_demand_forecasting_retrain inventory_writeoff_risk_retrain inventory_replenishment_retrain inventory_demand_forecasting_apply inventory_writeoff_risk_apply inventory_replenishment_apply"
	@echo "  Document intelligence:"
	@echo "    make dab-validate-document_intelligence"
	@echo "    make dab-deploy-document_intelligence"
	@echo "    make dab-run-document_intelligence RUN_JOB=<job-name>"
	@echo "      allowed RUN_JOB: document_intelligence_generate_job document_intelligence_pipeline_job"
	@echo "  AI Powered Insights:"
	@echo "    make dab-validate-ai_powered_insights"
	@echo "    make dab-deploy-ai_powered_insights"
	@echo "  Document intelligence (prescription PDFs; jobs map to DAB 1/2/3):"
	@echo "  make document-intelligence-install             - Install doc-intel deps (pdfplumber, loguru, faker, reportlab)"
	@echo "  make document-intelligence-generate-data      - Job 1: generate PDFs + labels (defaults; override DOCINT_NUM_PDFS and DOCINT_SEED via env)"
	@echo "  make document-intelligence-ocr                 - Job 2: OCR extraction → predictions/ocr/"
	@echo "  make document-intelligence-field-extraction    - Job 3: field extraction → predictions/fields/"
	@echo "  make document-intelligence-run                 - Full pipeline (OCR + field extraction) over local data/local/prescription_pdfs/"
	@echo "  make document-intelligence-app-run             - Run Streamlit annotator (review predictions) locally"
	@echo "  make document-intelligence-smoke             - Local smoke: generate → ocr → fields → start Streamlit briefly"
	@echo "  make document-intelligence-generate-pdfs       - Alias: generate PDFs via raw script (uses generator defaults)"
	@echo ""
	@echo "  Marvelous MLOps (separate venv; run marvelous-mlops-venv first):"
	@echo "  make marvelous-mlops-venv                 - Create .venv and install requirements in marvelous_mlops/"
	@echo "  make marvelous-mlops-fetch-medium         - Fetch Medium articles"
	@echo "  make marvelous-mlops-fetch-substack       - Fetch Substack posts"
	@echo "  make marvelous-mlops-fetch-youtube        - Fetch YouTube transcripts"

# --- Environment (databricks-misc): use uv if available, else python3/pip ---
uv-venv:
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv venv) || (command -v python3.12 >/dev/null 2>&1 && python3.12 -m venv .venv) || (command -v python3.11 >/dev/null 2>&1 && python3.11 -m venv .venv) || python3 -m venv .venv
	@echo "Created .venv. Next: make install  [make uv-dev for format tools]"

uv-sync:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync || .venv/bin/pip install -e .)
	@echo "Deps installed. For dev tools (autoflake, isort, black): make uv-dev"

install: uv-sync

uv-dev:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync --extra dev || .venv/bin/pip install -e ".[dev]")
	@echo "Dev deps installed."

uv-activate:
	@echo "Run: source $(REPO_ROOT)/.venv/bin/activate"

# --- MLflow UI (utils.mlflow; local env only) ---
mlflow-ui:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) -m utils.mlflow.run_ui

# --- Wipe local MLflow (utils.mlflow) ---
mlflow-wipe:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) -m utils.mlflow.wipe

# --- Cleanup ---
cleanup:
	find $(REPO_ROOT) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find $(REPO_ROOT) -type f -name "*.pyc" -delete 2>/dev/null || true
	find $(REPO_ROOT) -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf $(REPO_ROOT)/.pytest_cache $(REPO_ROOT)/.coverage $(REPO_ROOT)/.mypy_cache 2>/dev/null || true
	rm -rf $(REPO_ROOT)/data/healthcare_data_medallion/.databricks \
		$(REPO_ROOT)/data/healthcare_data_medallion/logs \
		$(REPO_ROOT)/data/healthcare_data_medallion/target 2>/dev/null || true
	find $(REPO_ROOT) -type d -name ".databricks" -exec rm -rf {} + 2>/dev/null || true
	find $(REPO_ROOT) -type d -name "target" -exec rm -rf {} + 2>/dev/null || true
	find $(REPO_ROOT) -type d -name "dbt_packages" -exec rm -rf {} + 2>/dev/null || true
	find $(REPO_ROOT) -type d -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null || true
	find $(REPO_ROOT) -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup done."

# --- Clean local data (generated CSVs, DuckDB, PDFs, dbt artifacts); start again ---
clean-local-data:
	rm -rf $(DATA_LOCAL_DIR) $(REPO_ROOT)/test_output $(REPO_ROOT)/$(DOC_INTEL_PDF_OUTPUT) $(REPO_ROOT)/prescription_pdfs 2>/dev/null || true
	rm -rf $(MEDALLION_DIR)/.databricks $(MEDALLION_DIR)/logs $(MEDALLION_DIR)/target $(MEDALLION_DIR)/dbt_packages 2>/dev/null || true
	@echo "Local data removed. Run make data-local-generate-quick (or data-local-generate) then data-local-duckdb-load and data-local-dbt-run to start again."

# --- Format (autoflake -> isort -> black); requires make uv-dev ---
FMT_ARGS ?= data use_cases
format:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make uv-dev" && exit 1)
	cd $(REPO_ROOT) && $(PY) -m autoflake $(FMT_ARGS) --remove-all-unused-imports --remove-unused-variables --recursive --in-place
	cd $(REPO_ROOT) && $(PY) -m isort $(FMT_ARGS)
	cd $(REPO_ROOT) && $(PY) -m black $(FMT_ARGS)
	@echo "Format done."

uc-foundation-deploy:
	@test -f $(REPO_ROOT)/bundles/uc_foundation/databricks.yml || (echo "Missing: bundles/uc_foundation/databricks.yml" && exit 1)
	@echo "Deploying UC foundation to target '$(UC_FOUNDATION_TARGET)'..."
	@$(MAKE) dab-deploy BUNDLE=uc_foundation DAB_TARGET=$(UC_FOUNDATION_TARGET) DAB_PROFILE=$(UC_FOUNDATION_TARGET)

# --- Local: data generation and medallion (repo root = source root) ---
data-local-generate:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) data/healthcare_data_generator/src/generate_local.py -o $(DATA_LOCAL_DIR)
	@echo "Healthcare CSVs in $(DATA_LOCAL_DIR)/"

data-local-generate-quick:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) data/healthcare_data_generator/src/generate_local.py -o $(DATA_LOCAL_DIR) --quick
	@echo "Healthcare CSVs (quick) in $(DATA_LOCAL_DIR)/"

data-local-generate-pdfs:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) data/prescription_pdf_generator/generate_prescription_pdfs_local.py
	@echo "Generated PDFs in $(DOC_INTEL_PDF_OUTPUT)/"

data-local-duckdb-load:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && REPO_ROOT=$(REPO_ROOT) DBT_DUCKDB_PATH=$(REPO_ROOT)/data/local/medallion.duckdb $(PY) data/healthcare_data_medallion/load_local_raw_to_duckdb.py \
		--csv-dir $(DATA_LOCAL_DIR) --duckdb-path $(REPO_ROOT)/data/local/medallion.duckdb
	@echo "DuckDB raw layer at $(REPO_ROOT)/data/local/medallion.duckdb"

data-local-dbt-run: data-local-duckdb-load
	@test -d $(MEDALLION_DIR) || (echo "Medallion dir missing: $(MEDALLION_DIR)" && exit 1)
	@test -x $(DBT_BIN) || (echo "dbt not found. Run: make install" && exit 1)
	cd $(MEDALLION_DIR) && DBT_PROFILES_DIR=$(MEDALLION_DIR)/dbt_profiles $(DBT_BIN) deps
	cd $(MEDALLION_DIR) && DBT_PROFILES_DIR=$(MEDALLION_DIR)/dbt_profiles DBT_DUCKDB_PATH=$(REPO_ROOT)/data/local/medallion.duckdb $(DBT_BIN) run --profile duckdb
	@echo "dbt run (duckdb) done."

data-local-dbt-test: data-local-dbt-run
	@test -d $(MEDALLION_DIR) || (echo "Medallion dir missing: $(MEDALLION_DIR)" && exit 1)
	@test -x $(DBT_BIN) || (echo "dbt not found. Run: make install" && exit 1)
	cd $(MEDALLION_DIR) && DBT_PROFILES_DIR=$(MEDALLION_DIR)/dbt_profiles DBT_DUCKDB_PATH=$(REPO_ROOT)/data/local/medallion.duckdb $(DBT_BIN) test --profile duckdb
	@echo "dbt test (duckdb) done."

# --- Document intelligence (jobs 1/2/3 + full pipeline + Streamlit app; defaults from config) ---
document-intelligence-install:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync --extra document_intelligence || .venv/bin/pip install -e ".[document_intelligence]")
	@echo "Document intelligence deps (pdfplumber, loguru, faker, reportlab) installed."

# Job 1: generate prescription PDFs + labels (same entrypoint as DAB document_intelligence_generate_job)
document-intelligence-generate-data:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make document-intelligence-install" && exit 1)
	cd $(REPO_ROOT) && DOCINT_DATA_SOURCE=local $(PY) use_cases/document_intelligence/jobs/1_generate_data.py
	@echo "document-intelligence generate-data done → $(DOC_INTEL_PDF_OUTPUT)/documents and $(DOC_INTEL_PDF_OUTPUT)/labels"

# Job 2: OCR extraction → predictions/ocr/
document-intelligence-ocr:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make document-intelligence-install" && exit 1)
	@test -d $(REPO_ROOT)/$(DOC_INTEL_PDF_OUTPUT)/documents || (echo "Run: make document-intelligence-generate-data first" && exit 1)
	cd $(REPO_ROOT) && DOCINT_DATA_SOURCE=local $(PY) use_cases/document_intelligence/jobs/2_ocr_extraction.py
	@echo "document-intelligence OCR done → $(DOC_INTEL_PDF_OUTPUT)/predictions/ocr/"

# Job 3: field extraction → predictions/fields/
document-intelligence-field-extraction:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make document-intelligence-install" && exit 1)
	@test -d $(REPO_ROOT)/$(DOC_INTEL_PDF_OUTPUT)/documents || (echo "Run: make document-intelligence-generate-data first" && exit 1)
	cd $(REPO_ROOT) && DOCINT_DATA_SOURCE=local $(PY) use_cases/document_intelligence/jobs/3_field_extraction.py
	@echo "document-intelligence field-extraction done → $(DOC_INTEL_PDF_OUTPUT)/predictions/fields/"

# Full pipeline (Job 2 + Job 3; assumes PDFs already exist)
document-intelligence-run:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make document-intelligence-install" && exit 1)
	@test -d $(REPO_ROOT)/$(DOC_INTEL_PDF_OUTPUT)/documents || (echo "Run: make document-intelligence-generate-data first" && exit 1)
	cd $(REPO_ROOT) && DOCINT_DATA_SOURCE=local $(PY) use_cases/document_intelligence/jobs/2_ocr_extraction.py
	cd $(REPO_ROOT) && DOCINT_DATA_SOURCE=local $(PY) use_cases/document_intelligence/jobs/3_field_extraction.py
	@echo "document-intelligence run done."

# Streamlit annotator app (review predictions from predictions/fields/)
document-intelligence-app-run:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make document-intelligence-install" && exit 1)
	@test -d $(REPO_ROOT)/$(DOC_INTEL_PDF_OUTPUT)/predictions/fields || (echo "Run: make document-intelligence-run (or generate-data + ocr + field-extraction) first so predictions/fields/ exists" && exit 1)
	cd $(REPO_ROOT) && $(PY) -m streamlit run use_cases/document_intelligence/annotator/app.py
	@echo "document-intelligence annotator app (Streamlit)"

document-intelligence-smoke:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make document-intelligence-install" && exit 1)
	cd $(REPO_ROOT) && DOCINT_DATA_SOURCE=local $(PY) use_cases/document_intelligence/run_document_intelligence_smoke.py
	@echo "document-intelligence smoke done"

# Alias: generate PDFs via raw generator script (alternative to job 1)
document-intelligence-generate-pdfs: data-local-generate-pdfs

# --- Recommendation engine (single entrypoint; RECO_DATA_SOURCE=local|catalog|auto) ---
reco-install:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync --extra reco || .venv/bin/pip install -e ".[reco]")
	@echo "Reco deps (implicit, lightgbm, mlflow) installed."

reco-data: data-local-generate-quick data-local-duckdb-load data-local-dbt-run

# Full sequence: generate medallion data → train/log MLflow models → MLflow-load apply
reco-run: reco-data
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	@echo "[reco] training+logging to MLflow, then loading via MLflow pyfunc..."
	cd $(REPO_ROOT) && $(PY) use_cases/recommendation_engine/models/run_reco_smoke.py
	@echo "reco run smoke done (train/log + MLflow load + apply)."

# Per-model reco entrypoints (train/apply)
reco-item-sim-train:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/recommendation_engine/models/item_similarity/train.py

reco-item-sim-apply:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/recommendation_engine/models/item_similarity/predict.py

reco-als-train:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/recommendation_engine/models/als/train.py

reco-als-apply:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/recommendation_engine/models/als/predict.py

reco-lightfm-train:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/recommendation_engine/models/lightfm/train.py

reco-lightfm-apply:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/recommendation_engine/models/lightfm/predict.py

# Streamlit app for recommendation engine
reco-app-run:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) -m streamlit run use_cases/recommendation_engine/app/app.py
	@echo "reco app running (Streamlit)"

# Streamlit app for AI Powered Insights (Genie + domain router)
ai-insights-app-run:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	@$(PY) -m pip install -r use_cases/ai_powered_insights/app/requirements.txt >/dev/null 2>&1 || true
	cd $(REPO_ROOT) && $(PY) -m streamlit run use_cases/ai_powered_insights/app/app.py
	@echo "ai-powered-insights app running (Streamlit)"

# --- Inventory optimisation (single entrypoint; INVENTORY_DATA_SOURCE=local|catalog|auto) ---
inventory-install:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync --extra inventory || .venv/bin/pip install -e ".[inventory]")
	@echo "Inventory deps (scipy, lightgbm) installed."

inventory-data: data-local-generate-quick data-local-duckdb-load data-local-dbt-run

# Full sequence: generate medallion data → train/log MLflow → MLflow-load apply (write-off risk)
inventory-run: inventory-data
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	@echo "[inventory] data ready (inventory-data). Installing inventory deps..."
	@$(MAKE) inventory-install
	@echo "[inventory] training+logging MLflow models, then loading back via smoke wrapper..."
	cd $(REPO_ROOT) && $(PY) use_cases/inventory_optimization/run_inventory_smoke.py
	@echo "inventory run smoke done (train/log + MLflow load + apply)."

# Per-model inventory entrypoints (train/apply)
inventory-writeoff-train:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/inventory_optimization/models/writeoff_risk/train.py

inventory-writeoff-apply:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/inventory_optimization/models/writeoff_risk/predict.py

inventory-demand-train:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/inventory_optimization/models/demand_forecasting/train.py

inventory-demand-apply:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/inventory_optimization/models/demand_forecasting/predict.py

inventory-replenishment-train:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/inventory_optimization/models/replenishment/train.py

inventory-replenishment-apply:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/inventory_optimization/models/replenishment/predict.py

# --- Marvelous MLOps (sub-usecase: own venv and requirements.txt) ---
marvelous-mlops-venv:
	cd $(MARVELOUS_MLOPS_DIR) && (command -v uv >/dev/null 2>&1 && uv venv || python3 -m venv .venv) && .venv/bin/pip install -r requirements.txt
	@echo "marvelous-mlops .venv ready. Run: make marvelous-mlops-fetch-medium|fetch-substack|fetch-youtube"

marvelous-mlops-fetch-medium:
	@test -x $(MARVELOUS_PY) || (echo "Run: make marvelous-mlops-venv" && exit 1)
	cd $(MARVELOUS_MLOPS_DIR) && $(MARVELOUS_PY) fetch_medium.py
	@echo "Medium fetch done."

marvelous-mlops-fetch-substack:
	@test -x $(MARVELOUS_PY) || (echo "Run: make marvelous-mlops-venv" && exit 1)
	cd $(MARVELOUS_MLOPS_DIR) && $(MARVELOUS_PY) fetch_substack.py
	@echo "Substack fetch done."

marvelous-mlops-fetch-youtube:
	@test -x $(MARVELOUS_PY) || (echo "Run: make marvelous-mlops-venv" && exit 1)
	cd $(MARVELOUS_MLOPS_DIR) && $(MARVELOUS_PY) fetch_youtube.py
	@echo "YouTube fetch done."

# --- Databricks Asset Bundles (DAB) ---
# Bundle-centric commands so CI/local dev can validate/deploy/run consistently.
#
# Usage:
#   make dab-validate BUNDLE=recommendation_engine DAB_TARGET=dev-sp
#   make dab-deploy   BUNDLE=inventory_optimization DAB_TARGET=test-sp
#   make dab-run      BUNDLE=document_intelligence RUN_JOB=document_intelligence_pipeline_job DAB_TARGET=prod-sp

DAB_TARGET ?= dev-sp
DAB_PROFILE ?= $(DAB_TARGET)
BUNDLE ?=
RUN_JOB ?=

define dab_bundle_dir
# Deprecated: BUNDLE_DIR mapping is handled directly in dab-validate/dab-deploy/dab-run.
endef

# Bundle "kind": job_multi | job_single | deploy_only
define dab_bundle_kind
$(if $(filter recommendation_engine,$(1)),job_multi,\
$(if $(filter inventory_optimization,$(1)),job_multi,\
$(if $(filter document_intelligence,$(1)),job_multi,\
$(if $(filter healthcare_data_generator,$(1)),job_single,\
$(if $(filter healthcare_data_medallion,$(1)),job_single,\
deploy_only\
)))))
endef

# Multi-job bundles: allowed RUN_JOB values (strict).
define dab_allowed_jobs
$(if $(filter recommendation_engine,$(1)),recommendation_engine_retrain recommendation_engine_lightfm_retrain recommendation_engine_apply recommendation_engine_lightfm_apply,\
$(if $(filter inventory_optimization,$(1)),inventory_demand_forecasting_retrain inventory_writeoff_risk_retrain inventory_replenishment_retrain inventory_demand_forecasting_apply inventory_writeoff_risk_apply inventory_replenishment_apply,\
$(if $(filter document_intelligence,$(1)),document_intelligence_generate_job document_intelligence_pipeline_job,\
)))
endef

# Some resources (Genie spaces and UC foundation) require direct deploy engine.
define dab_requires_direct_engine
$(if $(filter uc_foundation ai_powered_insights_genie_spaces,$(1)),1,)
endef

dab-list:
	@echo "Available DAB bundles:"
	@echo "  uc_foundation"
	@echo "  healthcare_data_generator"
	@echo "  healthcare_data_medallion"
	@echo "  recommendation_engine (job)"
	@echo "  recommendation_engine_serving (endpoints)"
	@echo "  recommendation_engine_app (databricks app)"
	@echo "  inventory_optimization (job)"
	@echo "  document_intelligence (job)"
	@echo "  document_intelligence_annotator_app (databricks app)"
	@echo "  ai_powered_insights_app (databricks app)"
	@echo "  ai_powered_insights_dashboards (dashboards)"
	@echo "  ai_powered_insights_genie_spaces (genie spaces)"

dab-validate:
	@test -n "$(strip $(BUNDLE))" || (echo "Usage: make dab-validate BUNDLE=<bundle-name> [DAB_TARGET=...]" && exit 1)
	@BUNDLE_DIR=""; \
	if [ "$(BUNDLE)" = "uc_foundation" ]; then BUNDLE_DIR="$(REPO_ROOT)/bundles/uc_foundation"; \
	elif [ "$(BUNDLE)" = "healthcare_data_generator" ]; then BUNDLE_DIR="$(REPO_ROOT)/data/healthcare_data_generator/bundles"; \
	elif [ "$(BUNDLE)" = "healthcare_data_medallion" ]; then BUNDLE_DIR="$(REPO_ROOT)/data/healthcare_data_medallion/bundles"; \
	elif [ "$(BUNDLE)" = "recommendation_engine" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/recommendation_engine/bundles/job"; \
	elif [ "$(BUNDLE)" = "recommendation_engine_serving" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/recommendation_engine/bundles/serving"; \
	elif [ "$(BUNDLE)" = "recommendation_engine_app" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/recommendation_engine/bundles/app"; \
	elif [ "$(BUNDLE)" = "inventory_optimization" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/inventory_optimization/bundles/job"; \
	elif [ "$(BUNDLE)" = "document_intelligence" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/document_intelligence/bundles/job"; \
	elif [ "$(BUNDLE)" = "document_intelligence_annotator_app" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/document_intelligence/bundles/app"; \
	elif [ "$(BUNDLE)" = "ai_powered_insights_app" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/ai_powered_insights/bundles/app"; \
	elif [ "$(BUNDLE)" = "ai_powered_insights_dashboards" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/ai_powered_insights/bundles/dashboards"; \
	elif [ "$(BUNDLE)" = "ai_powered_insights_genie_spaces" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/ai_powered_insights/bundles/genie_spaces"; \
	else BUNDLE_DIR=""; \
	fi; \
	if [ -z "$$BUNDLE_DIR" ] || [ ! -f "$$BUNDLE_DIR/databricks.yml" ]; then \
	  echo "Unknown/invalid bundle '$(BUNDLE)'. Try: make dab-list"; exit 1; \
	fi; \
	echo "[dab-validate] bundle=$(BUNDLE) dir=$$BUNDLE_DIR target=$(DAB_TARGET) profile=$(DAB_PROFILE)"; \
	if [ "$(call dab_requires_direct_engine,$(BUNDLE))" = "1" ]; then \
	  cd "$$BUNDLE_DIR" && DATABRICKS_BUNDLE_ENGINE=direct databricks bundle validate --target $(DAB_TARGET) --profile $(DAB_PROFILE); \
	else \
	  cd "$$BUNDLE_DIR" && databricks bundle validate --target $(DAB_TARGET) --profile $(DAB_PROFILE); \
	fi

dab-deploy:
	@test -n "$(strip $(BUNDLE))" || (echo "Usage: make dab-deploy BUNDLE=<bundle-name> [DAB_TARGET=...]" && exit 1)
	@BUNDLE_DIR=""; \
	if [ "$(BUNDLE)" = "uc_foundation" ]; then BUNDLE_DIR="$(REPO_ROOT)/bundles/uc_foundation"; \
	elif [ "$(BUNDLE)" = "healthcare_data_generator" ]; then BUNDLE_DIR="$(REPO_ROOT)/data/healthcare_data_generator/bundles"; \
	elif [ "$(BUNDLE)" = "healthcare_data_medallion" ]; then BUNDLE_DIR="$(REPO_ROOT)/data/healthcare_data_medallion/bundles"; \
	elif [ "$(BUNDLE)" = "recommendation_engine" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/recommendation_engine/bundles/job"; \
	elif [ "$(BUNDLE)" = "recommendation_engine_serving" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/recommendation_engine/bundles/serving"; \
	elif [ "$(BUNDLE)" = "recommendation_engine_app" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/recommendation_engine/bundles/app"; \
	elif [ "$(BUNDLE)" = "inventory_optimization" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/inventory_optimization/bundles/job"; \
	elif [ "$(BUNDLE)" = "document_intelligence" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/document_intelligence/bundles/job"; \
	elif [ "$(BUNDLE)" = "document_intelligence_annotator_app" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/document_intelligence/bundles/app"; \
	elif [ "$(BUNDLE)" = "ai_powered_insights_app" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/ai_powered_insights/bundles/app"; \
	elif [ "$(BUNDLE)" = "ai_powered_insights_dashboards" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/ai_powered_insights/bundles/dashboards"; \
	elif [ "$(BUNDLE)" = "ai_powered_insights_genie_spaces" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/ai_powered_insights/bundles/genie_spaces"; \
	else BUNDLE_DIR=""; \
	fi; \
	if [ -z "$$BUNDLE_DIR" ] || [ ! -f "$$BUNDLE_DIR/databricks.yml" ]; then \
	  echo "Unknown/invalid bundle '$(BUNDLE)'. Try: make dab-list"; exit 1; \
	fi; \
	echo "[dab-deploy] bundle=$(BUNDLE) dir=$$BUNDLE_DIR target=$(DAB_TARGET) profile=$(DAB_PROFILE)"; \
	if [ "$(call dab_requires_direct_engine,$(BUNDLE))" = "1" ]; then \
	  cd "$$BUNDLE_DIR" && DATABRICKS_BUNDLE_ENGINE=direct databricks bundle deploy --target $(DAB_TARGET) --profile $(DAB_PROFILE); \
	else \
	  cd "$$BUNDLE_DIR" && databricks bundle deploy --target $(DAB_TARGET) --profile $(DAB_PROFILE); \
	fi

dab-run:
	@test -n "$(strip $(BUNDLE))" || (echo "Usage: make dab-run BUNDLE=<bundle-name> RUN_JOB=<job-name> [DAB_TARGET=...]" && exit 1)
	@BUNDLE_KIND="$(call dab_bundle_kind,$(BUNDLE))"; \
	BUNDLE_DIR=""; \
	if [ "$(BUNDLE)" = "uc_foundation" ]; then BUNDLE_DIR="$(REPO_ROOT)/bundles/uc_foundation"; \
	elif [ "$(BUNDLE)" = "healthcare_data_generator" ]; then BUNDLE_DIR="$(REPO_ROOT)/data/healthcare_data_generator/bundles"; \
	elif [ "$(BUNDLE)" = "healthcare_data_medallion" ]; then BUNDLE_DIR="$(REPO_ROOT)/data/healthcare_data_medallion/bundles"; \
	elif [ "$(BUNDLE)" = "recommendation_engine" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/recommendation_engine/bundles/job"; \
	elif [ "$(BUNDLE)" = "recommendation_engine_serving" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/recommendation_engine/bundles/serving"; \
	elif [ "$(BUNDLE)" = "recommendation_engine_app" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/recommendation_engine/bundles/app"; \
	elif [ "$(BUNDLE)" = "inventory_optimization" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/inventory_optimization/bundles/job"; \
	elif [ "$(BUNDLE)" = "document_intelligence" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/document_intelligence/bundles/job"; \
	elif [ "$(BUNDLE)" = "document_intelligence_annotator_app" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/document_intelligence/bundles/app"; \
	elif [ "$(BUNDLE)" = "ai_powered_insights_app" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/ai_powered_insights/bundles/app"; \
	elif [ "$(BUNDLE)" = "ai_powered_insights_dashboards" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/ai_powered_insights/bundles/dashboards"; \
	elif [ "$(BUNDLE)" = "ai_powered_insights_genie_spaces" ]; then BUNDLE_DIR="$(REPO_ROOT)/use_cases/ai_powered_insights/bundles/genie_spaces"; \
	else BUNDLE_DIR=""; \
	fi; \
	ALLOWED_JOBS="$(call dab_allowed_jobs,$(BUNDLE))"; \
	if [ -z "$$BUNDLE_DIR" ] || [ ! -f "$$BUNDLE_DIR/databricks.yml" ]; then \
	  echo "Unknown/invalid bundle '$(BUNDLE)'. Try: make dab-list"; exit 1; \
	fi; \
	if [ "$$BUNDLE_KIND" = "deploy_only" ]; then \
	  echo "dab-run not supported for deploy-only bundle '$(BUNDLE)'. Use dab-deploy instead."; exit 1; \
	fi; \
	if [ "$$BUNDLE_KIND" = "job_single" ]; then \
	  if [ -n "$(strip $(RUN_JOB))" ]; then \
	    echo "RUN_JOB must be empty for single-job bundle '$(BUNDLE)'."; exit 1; \
	  fi; \
	  echo "[dab-run] bundle=$(BUNDLE) (single-job) dir=$$BUNDLE_DIR target=$(DAB_TARGET) profile=$(DAB_PROFILE)"; \
	  cd "$$BUNDLE_DIR" && databricks bundle run --target $(DAB_TARGET) --profile $(DAB_PROFILE); \
	else \
	  if [ -z "$(strip $(RUN_JOB))" ]; then \
	    echo "RUN_JOB is required for multi-job bundle '$(BUNDLE)'." ; \
	    echo "Allowed jobs: $$ALLOWED_JOBS"; exit 1; \
	  fi; \
	  case " $$ALLOWED_JOBS " in \
	    *" $(RUN_JOB) "*) ;; \
	    *) echo "Invalid RUN_JOB='$(RUN_JOB)' for bundle '$(BUNDLE)'. Allowed: $$ALLOWED_JOBS"; exit 1 ;; \
	  esac; \
	  echo "[dab-run] bundle=$(BUNDLE) job=$(RUN_JOB) dir=$$BUNDLE_DIR target=$(DAB_TARGET) profile=$(DAB_PROFILE)"; \
	  cd "$$BUNDLE_DIR" && databricks bundle run $(RUN_JOB) --target $(DAB_TARGET) --profile $(DAB_PROFILE); \
	fi

# --- Use-case DAB wrappers (readable use-case-specific commands) ---

dab-validate-recommendation_engine:
	@$(MAKE) dab-validate BUNDLE=recommendation_engine DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=recommendation_engine_serving DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=recommendation_engine_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-deploy-recommendation_engine:
	@$(MAKE) dab-deploy BUNDLE=recommendation_engine DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=recommendation_engine_serving DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=recommendation_engine_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-run-recommendation_engine:
	@test -n "$(strip $(RUN_JOB))" || (echo "Usage: make dab-run-recommendation_engine RUN_JOB=<job-name> [DAB_TARGET=...]" && exit 1)
	@$(MAKE) dab-run BUNDLE=recommendation_engine RUN_JOB=$(RUN_JOB) DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-validate-inventory_optimization:
	@$(MAKE) dab-validate BUNDLE=inventory_optimization DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-deploy-inventory_optimization:
	@$(MAKE) dab-deploy BUNDLE=inventory_optimization DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-run-inventory_optimization:
	@test -n "$(strip $(RUN_JOB))" || (echo "Usage: make dab-run-inventory_optimization RUN_JOB=<job-name> [DAB_TARGET=...]" && exit 1)
	@$(MAKE) dab-run BUNDLE=inventory_optimization RUN_JOB=$(RUN_JOB) DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-validate-document_intelligence:
	@$(MAKE) dab-validate BUNDLE=document_intelligence DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=document_intelligence_annotator_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-deploy-document_intelligence:
	@$(MAKE) dab-deploy BUNDLE=document_intelligence DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=document_intelligence_annotator_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-run-document_intelligence:
	@test -n "$(strip $(RUN_JOB))" || (echo "Usage: make dab-run-document_intelligence RUN_JOB=<job-name> [DAB_TARGET=...]" && exit 1)
	@$(MAKE) dab-run BUNDLE=document_intelligence RUN_JOB=$(RUN_JOB) DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-validate-ai_powered_insights:
	@$(MAKE) dab-validate BUNDLE=ai_powered_insights_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=ai_powered_insights_dashboards DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=ai_powered_insights_genie_spaces DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-deploy-ai_powered_insights:
	@$(MAKE) dab-deploy BUNDLE=ai_powered_insights_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=ai_powered_insights_dashboards DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=ai_powered_insights_genie_spaces DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

# Optional convenience: keep your old UC foundation deploy target name,
# but route it through dab-deploy to reuse the bundle framework.
uc-foundation-deploy-dab-wrapper:
	@$(MAKE) dab-deploy BUNDLE=uc_foundation DAB_TARGET=$(UC_FOUNDATION_TARGET) DAB_PROFILE=$(UC_FOUNDATION_TARGET)
