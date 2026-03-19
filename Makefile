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

# Default segment for bundle variable workspace_bundle_root = /Workspace/Users/<email> in databricks.yml.
# Override per deploy: databricks bundle deploy --var workspace_bundle_root=...  See: make dab-workspace-print
WORKSPACE_USER_EMAIL ?= sam.hardy@ebosgroup.com
WORKSPACE_BUNDLE_PREFIX := /Workspace/Users/$(WORKSPACE_USER_EMAIL)/.bundle

# Document intelligence (prescription PDFs): local base dir
DOC_INTEL_PDF_OUTPUT := data/local/prescription_pdfs

# Local Streamlit: rerun on save + file watcher (override e.g. STREAMLIT_LOCAL_OPTS=--server.fileWatcherType poll for Docker)
STREAMLIT_LOCAL_OPTS ?= --server.runOnSave true --server.fileWatcherType auto

# Marvelous MLOps: separate requirements, use sub-venv (make marvelous-mlops-venv first)
MARVELOUS_MLOPS_DIR := $(REPO_ROOT)/marvelous_mlops
MARVELOUS_PY := $(MARVELOUS_MLOPS_DIR)/.venv/bin/python

.PHONY: help test test-use-cases test-reco test-inventory test-doc-intel test-ai-insights
.PHONY: help cleanup clean-local-data format uc-foundation-deploy
.PHONY: dab-list dab-workspace-print dab-validate dab-deploy dab-destroy dab-run
.PHONY: foundation-dab-validate-uc foundation-dab-deploy-uc foundation-dab-destroy-uc
.PHONY: data-dab-validate-generator data-dab-deploy-generator data-dab-destroy-generator data-dab-run-generator
.PHONY: data-dab-validate-medallion data-dab-deploy-medallion data-dab-destroy-medallion data-dab-run-medallion
.PHONY: data-local-clean data-local-e2e use-cases-local-e2e
.PHONY: doc-intel-local-install doc-intel-local-ensure-spacy-model doc-intel-local-generate-data doc-intel-local-ocr doc-intel-local-field-extraction doc-intel-local-app-run doc-intel-local-smoke doc-intel-local-generate-pdfs
.PHONY: doc-intel-dab-validate doc-intel-dab-deploy doc-intel-dab-destroy doc-intel-dab-run-generate doc-intel-dab-run-pipeline
.PHONY: reco-local-install reco-local-data reco-local-run reco-local-e2e reco-local-item-sim-train reco-local-item-sim-apply reco-local-als-train reco-local-als-apply reco-local-lightfm-train reco-local-lightfm-apply reco-local-ranker-train reco-local-ranker-apply reco-local-app-run
.PHONY: reco-local-smoke reco-build-training-base
.PHONY: reco-dab-validate reco-dab-deploy reco-dab-destroy dab-destroy-reco reco-dab-run-build-training-base reco-dab-run-retrain reco-dab-run-apply reco-dab-run-lightfm-retrain reco-dab-run-lightfm-apply reco-dab-run-ranker-retrain reco-dab-run-ranker-apply
.PHONY: inventory-local-install inventory-local-data inventory-local-run inventory-local-e2e inventory-local-writeoff-train inventory-local-writeoff-apply inventory-local-demand-train inventory-local-demand-apply inventory-local-replenishment-train inventory-local-replenishment-apply
.PHONY: inventory-local-smoke
.PHONY: inventory-dab-validate inventory-dab-deploy inventory-dab-destroy inventory-dab-run-demand-retrain inventory-dab-run-writeoff-retrain inventory-dab-run-replenishment-retrain inventory-dab-run-demand-apply inventory-dab-run-writeoff-apply inventory-dab-run-replenishment-apply
.PHONY: ai-insights-local-app-run ai-insights-dab-validate ai-insights-dab-deploy ai-insights-dab-destroy
.PHONY: data-local-generate data-local-generate-quick data-local-generate-pdfs data-local-duckdb-load data-local-dbt-run data-local-dbt-test
.PHONY: reco-data reco-run reco-install reco-item-sim-train reco-item-sim-apply reco-als-train reco-als-apply reco-lightfm-train reco-lightfm-apply reco-ranker-train reco-ranker-apply reco-app-run
.PHONY: ai-insights-app-run
.PHONY: inventory-data inventory-run inventory-install inventory-writeoff-train inventory-writeoff-apply inventory-demand-train inventory-demand-apply inventory-replenishment-train inventory-replenishment-apply
.PHONY: document-intelligence-install document-intelligence-ensure-spacy-model document-intelligence-generate-pdfs document-intelligence-generate-data document-intelligence-ocr document-intelligence-field-extraction document-intelligence-run document-intelligence-app-run document-intelligence-smoke
.PHONY: mlflow-ui mlflow-wipe
.PHONY: marvelous-mlops-venv marvelous-mlops-fetch-medium marvelous-mlops-fetch-substack marvelous-mlops-fetch-youtube
.PHONY: uv-venv uv-sync install uv-dev uv-activate
.PHONY: bootstrap-system-tools bootstrap-system-tools-uv bootstrap-system-tools-databricks

help:
	@echo "Targets:"
	@echo "  ## Local env/util"
	@echo "  make uv-venv              - Create .venv (uses uv if available, else python3 -m venv)"
	@echo "  make uv-sync / install     - Install deps; use install then uv-dev for dev tools"
	@echo "  make uv-dev               - Install dev deps (autoflake, isort, black, pytest)"
	@echo "  make test / test-use-cases - pytest nominal tests for all use cases (requires uv-dev)"
	@echo "  make test-reco             - pytest recommendation_engine/tests only"
	@echo "  make test-inventory       - pytest inventory_optimization/tests only"
	@echo "  make test-doc-intel       - pytest document_intelligence/tests only"
	@echo "  make test-ai-insights     - pytest ai_powered_insights/tests only"
	@echo "  make uv-activate          - Print activate command for .venv"
	@echo "  STREAMLIT_LOCAL_OPTS       - Make variable: default '--server.runOnSave true ...' for *-app-run; see .streamlit/config.toml"
	@echo "  make bootstrap-system-tools - Chicken/egg: uv + Databricks CLI into \$$HOME/.local/bin (curl/unzip; override DATABRICKS_CLI_VERSION=)"
	@echo "  make cleanup              - Remove __pycache__, .pyc, .pytest_cache, .coverage, etc."
	@echo "  make format [FMT_ARGS=.]  - Run autoflake, isort, black"
	@echo "  make mlflow-ui            - Start MLflow UI (utils.mlflow, local only); http://localhost:5001"
	@echo "  make mlflow-wipe          - Remove local MLflow DB and artifacts (experiments, runs, registry)"
	@echo ""
	@echo "  ## Marvelous MLOps DBX Policy Generation"
	@echo "  make marvelous-mlops-venv                 - Create .venv and install requirements in marvelous_mlops/"
	@echo "  make marvelous-mlops-fetch-medium         - Fetch Medium articles"
	@echo "  make marvelous-mlops-fetch-substack       - Fetch Substack posts"
	@echo "  make marvelous-mlops-fetch-youtube        - Fetch YouTube transcripts"
	@echo ""
	@echo "  ## Databricks Asset Bundles (low-level):"
	@echo "  make dab-list                    - List BUNDLE= names for dab-validate / dab-deploy / dab-destroy / dab-run"
	@echo "  make dab-destroy BUNDLE=...      - databricks bundle destroy (optional DAB_DESTROY_AUTO_APPROVE=1)"
	@echo ""
	@echo "  ## UC foundation (Unity Catalog schemas/volumes):"
	@echo "  make uc-foundation-deploy        - Deploy bundles/uc_foundation to $(UC_FOUNDATION_TARGET) (compat)"
	@echo "  make foundation-dab-validate-uc  - Validate UC foundation bundle (DAB)"
	@echo "  make foundation-dab-deploy-uc    - Deploy UC foundation bundle (DAB)"
	@echo "  make foundation-dab-destroy-uc     - Destroy UC foundation bundle resources (DAB destroy)"
	@echo ""
	@echo "  ## Data foundation"
	@echo "  make data-local-clean           - Remove data/local/, test_output/, doc-intel PDFs, medallion target/logs (start again)"
	@echo "  make data-local-generate        - Generate healthcare CSVs to data/local/ (default sizes)"
	@echo "  make data-local-duckdb-load     - Load data/local/*.csv into DuckDB as raw schema (run after generate)"
	@echo "  make data-local-dbt-run         - Load data/local into DuckDB then run medallion dbt"
	@echo "  make data-local-dbt-test        - Build medallion (dbt run) then run dbt tests (referential integrity, etc.)"
	@echo "  make data-local-e2e             - End-to-end local: clean -> generate -> duckdb-load -> dbt-run -> dbt-test"
	@echo "  make use-cases-local-e2e        - data-local-e2e then reco, inventory, doc-intel local e2e (sequential)"
	@echo ""
	@echo "  make data-dab-validate-generator - Validate healthcare data generator bundle"
	@echo "  make data-dab-deploy-generator   - Deploy healthcare data generator bundle"
	@echo "  make data-dab-destroy-generator  - Destroy healthcare data generator bundle (DAB destroy)"
	@echo "  make data-dab-run-generator      - Run healthcare data generator job bundle"
	@echo "  make data-dab-validate-medallion - Validate healthcare medallion (dbt) bundle"
	@echo "  make data-dab-deploy-medallion   - Deploy healthcare medallion (dbt) bundle"
	@echo "  make data-dab-destroy-medallion  - Destroy healthcare medallion bundle (DAB destroy)"
	@echo "  make data-dab-run-medallion      - Run healthcare medallion (dbt) job bundle"
	@echo ""
	@echo "  ## AI Powered Insights (ai-insights):"
	@echo "  make ai-insights-local-app-run      - Run Streamlit router app locally"
	@echo "  make ai-insights-dab-validate       - Validate AI Insights bundles (app + dashboards + genie spaces)"
	@echo "  make ai-insights-dab-deploy         - Deploy AI Insights bundles (app + dashboards + genie spaces)"
	@echo "  make ai-insights-dab-destroy        - Destroy AI Insights bundles (reverse deploy order)"
	@echo ""
	@echo "  ## Document intelligence (doc-intel):"
	@echo "  make doc-intel-local-install        - Install doc-intel deps"
	@echo "  make doc-intel-local-ensure-spacy-model - pip install en_core_web_sm wheel if missing (ENSURE_SPACY_ARGS=--check-only for CI)"
	@echo "  make doc-intel-local-generate-data  - Local Job 1: generate PDFs + labels"
	@echo "  make doc-intel-local-ocr            - Local Job 2: OCR extraction"
	@echo "  make doc-intel-local-field-extraction - Local Job 3: field extraction"
	@echo "  make doc-intel-local-app-run        - Local Streamlit annotator"
	@echo "  make doc-intel-local-e2e            - Local end-to-end test"
	@echo ""
	@echo "  make doc-intel-dab-validate         - Validate doc-intel bundles (jobs + annotator app)"
	@echo "  make doc-intel-dab-deploy           - Deploy doc-intel bundles (jobs + annotator app)"
	@echo "  make doc-intel-dab-destroy          - Destroy doc-intel bundles (annotator app, then jobs)"
	@echo "  make doc-intel-dab-run-generate     - Run remote Job 1 (document_intelligence_generate_job)"
	@echo "  make doc-intel-dab-run-pipeline     - Run remote pipeline job (document_intelligence_pipeline_job)"
	@echo ""
	@echo "  ## Inventory optimisation (inventory):"
	@echo "  make inventory-local-install        - Install inventory deps"
	@echo "  make inventory-local-data           - Prepare local data/medallion (quick)"
	@echo "  make inventory-local-writeoff-train - Train write-off risk classifier"
	@echo "  make inventory-local-writeoff-apply - Apply write-off risk classifier"
	@echo "  make inventory-local-demand-train   - Train demand forecasting models"
	@echo "  make inventory-local-demand-apply   - Apply demand forecasting models"
	@echo "  make inventory-local-replenishment-train - Recompute replenishment policy"
	@echo "  make inventory-local-replenishment-apply - Apply replenishment policy"
	@echo "  make inventory-local-e2e            - Local end-to-end pipeline"
	@echo ""
	@echo "  make inventory-dab-validate         - Validate inventory job bundle"
	@echo "  make inventory-dab-deploy           - Deploy inventory job bundle"
	@echo "  make inventory-dab-destroy          - Destroy inventory job bundle (DAB destroy)"
	@echo "  make inventory-dab-run-demand-retrain       - Run demand forecasting retrain job"
	@echo "  make inventory-dab-run-writeoff-retrain     - Run writeoff risk retrain job"
	@echo "  make inventory-dab-run-replenishment-retrain - Run replenishment retrain job"
	@echo "  make inventory-dab-run-demand-apply         - Run demand forecasting apply job"
	@echo "  make inventory-dab-run-writeoff-apply       - Run writeoff risk apply job"
	@echo "  make inventory-dab-run-replenishment-apply  - Run replenishment apply job"
	@echo ""
	@echo "  ## Recommendation engine (reco):"
	@echo "  make reco-local-install        - Install reco deps"
	@echo "  make reco-local-data           - Prepare local data/medallion (quick)"
	@echo "  make reco-build-training-base  - Build gold_reco_training_base from silver (use-case transform)"
	@echo "  make reco-local-item-sim-train - Train item-similarity model"
	@echo "  make reco-local-item-sim-apply - Apply item-similarity model"
	@echo "  make reco-local-als-train      - Train ALS model"
	@echo "  make reco-local-als-apply      - Apply ALS model"
	@echo "  make reco-local-lightfm-train  - Train LightFM model"
	@echo "  make reco-local-lightfm-apply  - Apply LightFM model"
	@echo "  make reco-local-ranker-train   - Train ranker model"
	@echo "  make reco-local-ranker-apply   - Apply ranker model"
	@echo "  make reco-local-app-run        - Run reco Streamlit app locally"
	@echo "  make reco-local-e2e            - Local end-to-end pipeline"
	@echo ""
	@echo "  make reco-dab-validate         - Validate reco bundles (jobs + serving + app)"
	@echo "  make reco-dab-deploy           - Deploy reco bundles (jobs + serving + app)"
	@echo "  make reco-dab-destroy / dab-destroy-reco - Destroy reco bundles (app + serving + jobs)"
	@echo "  make reco-dab-run-build-training-base - Run reco build_training_base job"
	@echo "  make reco-dab-run-retrain      - Run reco retrain job (recommendation_engine_retrain)"
	@echo "  make reco-dab-run-apply        - Run reco apply job (recommendation_engine_apply)"
	@echo "  make reco-dab-run-lightfm-retrain - Run LightFM retrain job"
	@echo "  make reco-dab-run-lightfm-apply   - Run LightFM apply job"
	@echo "  make reco-dab-run-ranker-retrain  - Run ranker retrain job"
	@echo "  make reco-dab-run-ranker-apply    - Run ranker apply job"

# --- Environment (databricks-misc): use uv if available, else python3/pip ---
uv-venv:
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv venv) || (command -v python3.12 >/dev/null 2>&1 && python3.12 -m venv .venv) || (command -v python3.11 >/dev/null 2>&1 && python3.11 -m venv .venv) || python3 -m venv .venv
	@echo "Created .venv. Next: make install  [make uv-dev for format tools]"

uv-sync:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync || .venv/bin/pip install -e .)
	@echo "Deps installed. For dev tools (format + pytest): make uv-dev"

install: uv-sync

uv-dev:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync --extra dev || .venv/bin/pip install -e ".[dev]")
	@echo "Dev deps installed."

uv-activate:
	@echo "Run: source $(REPO_ROOT)/.venv/bin/activate"

# --- Use-case nominal tests (pytest; install dev extra first: make uv-dev) ---
test: test-use-cases

test-use-cases:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make uv-dev first" && exit 1)
	$(PY) -m pytest \
		$(REPO_ROOT)/use_cases/recommendation_engine/tests \
		$(REPO_ROOT)/use_cases/inventory_optimization/tests \
		$(REPO_ROOT)/use_cases/document_intelligence/tests \
		$(REPO_ROOT)/use_cases/ai_powered_insights/tests \
		-q

test-reco:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make uv-dev first" && exit 1)
	$(PY) -m pytest $(REPO_ROOT)/use_cases/recommendation_engine/tests -q

test-inventory:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make uv-dev first" && exit 1)
	$(PY) -m pytest $(REPO_ROOT)/use_cases/inventory_optimization/tests -q

test-doc-intel:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make uv-dev first" && exit 1)
	$(PY) -m pytest $(REPO_ROOT)/use_cases/document_intelligence/tests -q

test-ai-insights:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make uv-dev first" && exit 1)
	$(PY) -m pytest $(REPO_ROOT)/use_cases/ai_powered_insights/tests -q

# --- Bootstrap OS-level tools (before uv-venv / databricks bundle) ---
# Default CLI version: bump when you want DAB/CLI parity; override: make bootstrap-system-tools DATABRICKS_CLI_VERSION=0.296.0
# Install location: ensure $$HOME/.local/bin is on PATH ahead of any legacy /usr/local/bin databricks.
DATABRICKS_CLI_VERSION ?= 0.295.0
INSTALL_BIN_DIR ?= $(HOME)/.local/bin

bootstrap-system-tools: bootstrap-system-tools-uv bootstrap-system-tools-databricks
	@echo ""
	@echo "bootstrap-system-tools: done."
	@echo "Add to PATH if needed: export PATH=\"$(INSTALL_BIN_DIR):\$$PATH\""
	@echo "Then: cd $(REPO_ROOT) && make uv-venv && make install"

bootstrap-system-tools-uv:
	@echo "[bootstrap] uv (astral install.sh; or self-update if already on PATH)..."
	@command -v curl >/dev/null 2>&1 || (echo "curl is required" && exit 1)
	@if command -v uv >/dev/null 2>&1; then \
		echo "uv already: $$(command -v uv) ($$(uv --version))"; \
		uv self update || true; \
	else \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi

bootstrap-system-tools-databricks:
	@echo "[bootstrap] Databricks CLI v$(DATABRICKS_CLI_VERSION) -> $(INSTALL_BIN_DIR)"
	@command -v curl >/dev/null 2>&1 || (echo "curl is required" && exit 1)
	@command -v unzip >/dev/null 2>&1 || (echo "unzip is required" && exit 1)
	@set -e; \
	VERSION="$(DATABRICKS_CLI_VERSION)"; \
	BIN="$(INSTALL_BIN_DIR)"; \
	OS=$$(uname -s | cut -d- -f1); \
	ARCH=$$(uname -m); \
	case "$$OS" in \
		Darwin) O=darwin ;; \
		Linux) O=linux ;; \
		*) echo "Unsupported OS: $$OS (see https://docs.databricks.com/aws/en/dev-tools/cli/install)"; exit 1 ;; \
	esac; \
	case "$$ARCH" in \
		x86_64) A=amd64 ;; \
		amd64) A=amd64 ;; \
		arm64|aarch64) A=arm64 ;; \
		*) echo "Unsupported CPU arch: $$ARCH"; exit 1 ;; \
	esac; \
	FILE="databricks_cli_$${VERSION}_$${O}_$${A}"; \
	mkdir -p "$$BIN"; \
	TMP=$$(mktemp -d); \
	trap 'rm -rf "$$TMP"' EXIT; \
	cd "$$TMP"; \
	curl -fsSL -o databricks_cli.zip "https://github.com/databricks/cli/releases/download/v$${VERSION}/$${FILE}.zip"; \
	unzip -q -o databricks_cli.zip; \
	chmod +x databricks; \
	cp -f databricks "$$BIN/databricks"; \
	"$$BIN/databricks" version; \
	echo "Installed $$BIN/databricks"

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
	@echo "Local data removed. Next: make data-local-generate then data-local-duckdb-load and data-local-dbt-run (or just make data-local-e2e)."

# Canonical local clean (compat wrapper keeps working)
data-local-clean: clean-local-data

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
	@$(MAKE) data-local-generate

# End-to-end local data foundation (clean -> generate -> duckdb -> dbt run -> dbt test)
# Do not run data-local-e2e, reco-local-e2e, inventory-local-e2e in parallel; they share data/local/medallion.duckdb and will hit DuckDB lock errors.
data-local-e2e: data-local-clean data-local-generate data-local-duckdb-load data-local-dbt-run data-local-dbt-test
	@echo "data-local-e2e done."

# Full local verification: shared medallion (exclusive DuckDB) then each use-case smoke/e2e target.
# Do not run in parallel with other jobs using data/local/medallion.duckdb.
use-cases-local-e2e: data-local-e2e reco-local-install reco-local-e2e inventory-local-e2e doc-intel-local-install doc-intel-local-e2e
	@echo "use-cases-local-e2e: all steps done."

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
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync --extra dev --extra document_intelligence || .venv/bin/pip install -e ".[document_intelligence]")
	@echo "Document intelligence deps installed (includes en_core_web_sm via uv optional extra)."

# Ensure en_core_web_sm is loadable (pip install pinned wheel if missing; use --check-only for CI)
document-intelligence-ensure-spacy-model:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/document_intelligence/ensure_spacy_model.py $(ENSURE_SPACY_ARGS)

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
	cd $(REPO_ROOT) && $(PY) -m streamlit run use_cases/document_intelligence/annotator/app.py $(STREAMLIT_LOCAL_OPTS)
	@echo "document-intelligence annotator app (Streamlit)"

document-intelligence-smoke:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make document-intelligence-install" && exit 1)
	cd $(REPO_ROOT) && DOCINT_DATA_SOURCE=local $(PY) use_cases/document_intelligence/run_document_intelligence_smoke.py
	@echo "document-intelligence smoke done"

# Alias: generate PDFs via raw generator script (alternative to job 1)
document-intelligence-generate-pdfs: data-local-generate-pdfs

# ============================
# Canonical use-case targets
# ============================

# --- doc-intel (local) ---
doc-intel-local-install: document-intelligence-install
doc-intel-local-ensure-spacy-model: document-intelligence-ensure-spacy-model
doc-intel-local-generate-data: document-intelligence-generate-data
doc-intel-local-ocr: document-intelligence-ocr
doc-intel-local-field-extraction: document-intelligence-field-extraction
doc-intel-local-app-run: document-intelligence-app-run
doc-intel-local-smoke: document-intelligence-smoke
doc-intel-local-e2e: doc-intel-local-smoke
doc-intel-local-generate-pdfs: document-intelligence-generate-pdfs

# --- doc-intel (DAB) ---
doc-intel-dab-validate:
	@$(MAKE) dab-validate BUNDLE=document_intelligence DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=document_intelligence_annotator_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

doc-intel-dab-deploy:
	@$(MAKE) dab-deploy BUNDLE=document_intelligence DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=document_intelligence_annotator_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

doc-intel-dab-destroy:
	@$(MAKE) dab-destroy-document_intelligence DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

doc-intel-dab-run-generate:
	@$(MAKE) dab-run BUNDLE=document_intelligence RUN_JOB=document_intelligence_generate_job DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

doc-intel-dab-run-pipeline:
	@$(MAKE) dab-run BUNDLE=document_intelligence RUN_JOB=document_intelligence_pipeline_job DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

# --- Recommendation engine (single entrypoint; RECO_DATA_SOURCE=local|catalog|auto) ---
reco-install:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync --extra dev --extra reco || .venv/bin/pip install -e ".[reco]")
	@echo "Reco deps (implicit, lightgbm, mlflow) installed."

reco-data: data-local-generate-quick data-local-duckdb-load data-local-dbt-run

# Use-case-owned transform: build gold_reco_training_base from silver (run before train when using catalog or local parquet).
reco-build-training-base:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	cd $(REPO_ROOT) && RECO_DATA_SOURCE=local DBT_DUCKDB_PATH=$(RECO_LOCAL_DUCKDB_PATH) $(PY) use_cases/recommendation_engine/pipelines/build_training_base.py
	@echo "reco training base built (data/local/reco/gold_reco_training_base.parquet)."

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

reco-ranker-train:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/recommendation_engine/models/ranker/train.py

reco-ranker-apply:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) use_cases/recommendation_engine/models/ranker/predict.py

# Streamlit app for recommendation engine
reco-app-run:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install && make reco-install" && exit 1)
	cd $(REPO_ROOT) && $(PY) -m streamlit run use_cases/recommendation_engine/app/app.py $(STREAMLIT_LOCAL_OPTS)
	@echo "reco app running (Streamlit)"

# Streamlit app for AI Powered Insights (Genie + domain router)
ai-insights-app-run:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	@$(PY) -m pip install -r use_cases/ai_powered_insights/app/requirements.txt >/dev/null 2>&1 || true
	cd $(REPO_ROOT) && $(PY) -m streamlit run use_cases/ai_powered_insights/app/app.py $(STREAMLIT_LOCAL_OPTS)
	@echo "ai-powered-insights app running (Streamlit)"

# --- Inventory optimisation (single entrypoint; INVENTORY_DATA_SOURCE=local|catalog|auto) ---
inventory-install:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv first" && exit 1)
	cd $(REPO_ROOT) && (command -v uv >/dev/null 2>&1 && uv sync --extra dev --extra inventory || .venv/bin/pip install -e ".[inventory]")
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

ai-insights-local-app-run: ai-insights-app-run

# --- reco (local) ---
reco-local-install: reco-install
reco-local-data: reco-data
reco-local-smoke: reco-local-run
# Local e2e: data, use-case transform (gold_reco_training_base), then train/apply smoke.
reco-local-e2e: reco-local-data reco-build-training-base
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make reco-install" && exit 1)
	@echo "[reco-local] running train+apply smoke (DuckDB + local training base)..."
	cd $(REPO_ROOT) && RECO_DATA_SOURCE=local DBT_DUCKDB_PATH=$(RECO_LOCAL_DUCKDB_PATH) $(PY) use_cases/recommendation_engine/models/run_reco_smoke.py
	@echo "reco-local-e2e done."
reco-local-item-sim-train: reco-item-sim-train
reco-local-item-sim-apply: reco-item-sim-apply
reco-local-als-train: reco-als-train
reco-local-als-apply: reco-als-apply
reco-local-lightfm-train: reco-lightfm-train
reco-local-lightfm-apply: reco-lightfm-apply
reco-local-ranker-train: reco-ranker-train
reco-local-ranker-apply: reco-ranker-apply
reco-local-app-run: reco-app-run

# Local reco run should always use the local DuckDB medallion (avoid RECO_* catalog schema envs).
RECO_LOCAL_DUCKDB_PATH ?= $(REPO_ROOT)/data/local/medallion.duckdb
reco-local-run: reco-local-data reco-local-install
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install && make reco-local-install" && exit 1)
	@test -f $(RECO_LOCAL_DUCKDB_PATH) || (echo "Missing DuckDB medallion at $(RECO_LOCAL_DUCKDB_PATH). Run: make data-local-e2e (or data-local-dbt-run)" && exit 1)
	@echo "[reco-local] training+logging to MLflow, then loading via MLflow pyfunc (DuckDB medallion)..."
	cd $(REPO_ROOT) && RECO_DATA_SOURCE=local DBT_DUCKDB_PATH=$(RECO_LOCAL_DUCKDB_PATH) $(PY) use_cases/recommendation_engine/models/run_reco_smoke.py
	@echo "reco-local run done."

# --- reco (DAB) ---
reco-dab-validate:
	@$(MAKE) dab-validate BUNDLE=recommendation_engine DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=recommendation_engine_serving DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=recommendation_engine_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

reco-dab-deploy:
	@$(MAKE) dab-deploy BUNDLE=recommendation_engine DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=recommendation_engine_serving DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=recommendation_engine_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

reco-dab-destroy:
	@$(MAKE) dab-destroy-recommendation_engine DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

reco-dab-run-build-training-base:
	@$(MAKE) dab-run BUNDLE=recommendation_engine RUN_JOB=recommendation_engine_build_training_base DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

reco-dab-run-retrain:
	@$(MAKE) dab-run BUNDLE=recommendation_engine RUN_JOB=recommendation_engine_retrain DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

reco-dab-run-apply:
	@$(MAKE) dab-run BUNDLE=recommendation_engine RUN_JOB=recommendation_engine_apply DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

reco-dab-run-lightfm-retrain:
	@$(MAKE) dab-run BUNDLE=recommendation_engine RUN_JOB=recommendation_engine_lightfm_retrain DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

reco-dab-run-lightfm-apply:
	@$(MAKE) dab-run BUNDLE=recommendation_engine RUN_JOB=recommendation_engine_lightfm_apply DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

reco-dab-run-ranker-retrain:
	@$(MAKE) dab-run BUNDLE=recommendation_engine RUN_JOB=recommendation_engine_ranker_retrain DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

reco-dab-run-ranker-apply:
	@$(MAKE) dab-run BUNDLE=recommendation_engine RUN_JOB=recommendation_engine_ranker_apply DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

# --- inventory (local) ---
inventory-local-install: inventory-install
inventory-local-data: inventory-data
inventory-local-smoke: inventory-local-run
inventory-local-e2e: inventory-local-run
inventory-local-writeoff-train: inventory-writeoff-train
inventory-local-writeoff-apply: inventory-writeoff-apply
inventory-local-demand-train: inventory-demand-train
inventory-local-demand-apply: inventory-demand-apply
inventory-local-replenishment-train: inventory-replenishment-train
inventory-local-replenishment-apply: inventory-replenishment-apply

# Local inventory run should always use the local DuckDB medallion (avoid INVENTORY_* catalog schema envs).
INVENTORY_LOCAL_DUCKDB_PATH ?= $(REPO_ROOT)/data/local/medallion.duckdb
inventory-local-run: inventory-local-data inventory-local-install
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install && make inventory-local-install" && exit 1)
	@test -f $(INVENTORY_LOCAL_DUCKDB_PATH) || (echo "Missing DuckDB medallion at $(INVENTORY_LOCAL_DUCKDB_PATH). Run: make data-local-e2e (or data-local-dbt-run)" && exit 1)
	@echo "[inventory-local] running inventory smoke (DuckDB medallion)..."
	cd $(REPO_ROOT) && INVENTORY_DATA_SOURCE=local DBT_DUCKDB_PATH=$(INVENTORY_LOCAL_DUCKDB_PATH) $(PY) use_cases/inventory_optimization/run_inventory_smoke.py
	@echo "inventory-local run done."

# --- inventory (DAB) ---
inventory-dab-validate:
	@$(MAKE) dab-validate BUNDLE=inventory_optimization DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

inventory-dab-deploy:
	@$(MAKE) dab-deploy BUNDLE=inventory_optimization DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

inventory-dab-destroy:
	@$(MAKE) dab-destroy-inventory_optimization DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

inventory-dab-run-demand-retrain:
	@$(MAKE) dab-run BUNDLE=inventory_optimization RUN_JOB=inventory_demand_forecasting_retrain DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

inventory-dab-run-writeoff-retrain:
	@$(MAKE) dab-run BUNDLE=inventory_optimization RUN_JOB=inventory_writeoff_risk_retrain DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

inventory-dab-run-replenishment-retrain:
	@$(MAKE) dab-run BUNDLE=inventory_optimization RUN_JOB=inventory_replenishment_retrain DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

inventory-dab-run-demand-apply:
	@$(MAKE) dab-run BUNDLE=inventory_optimization RUN_JOB=inventory_demand_forecasting_apply DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

inventory-dab-run-writeoff-apply:
	@$(MAKE) dab-run BUNDLE=inventory_optimization RUN_JOB=inventory_writeoff_risk_apply DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

inventory-dab-run-replenishment-apply:
	@$(MAKE) dab-run BUNDLE=inventory_optimization RUN_JOB=inventory_replenishment_apply DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

# --- ai-insights (DAB) ---
ai-insights-dab-validate:
	@$(MAKE) dab-validate BUNDLE=ai_powered_insights_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=ai_powered_insights_dashboards DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=ai_powered_insights_genie_spaces DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

ai-insights-dab-deploy:
	@$(MAKE) dab-deploy BUNDLE=ai_powered_insights_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=ai_powered_insights_dashboards DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=ai_powered_insights_genie_spaces DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

ai-insights-dab-destroy:
	@$(MAKE) dab-destroy-ai_powered_insights DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

# --- foundation/data (DAB) ---
foundation-dab-validate-uc:
	@$(MAKE) dab-validate BUNDLE=uc_foundation DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

foundation-dab-deploy-uc:
	@$(MAKE) dab-deploy BUNDLE=uc_foundation DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

foundation-dab-destroy-uc:
	@$(MAKE) dab-destroy-uc_foundation DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

data-dab-validate-generator:
	@$(MAKE) dab-validate BUNDLE=healthcare_data_generator DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

data-dab-deploy-generator:
	@$(MAKE) dab-deploy BUNDLE=healthcare_data_generator DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

data-dab-destroy-generator:
	@$(MAKE) dab-destroy-healthcare_data_generator DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

data-dab-run-generator:
	@$(MAKE) dab-run BUNDLE=healthcare_data_generator DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

data-dab-validate-medallion:
	@$(MAKE) dab-validate BUNDLE=healthcare_data_medallion DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

data-dab-deploy-medallion:
	@$(MAKE) dab-deploy BUNDLE=healthcare_data_medallion DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

data-dab-destroy-medallion:
	@$(MAKE) dab-destroy-healthcare_data_medallion DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

data-dab-run-medallion:
	@$(MAKE) dab-run BUNDLE=healthcare_data_medallion DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

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
# Bundle-centric commands so CI/local dev can validate/deploy/run/destroy consistently.
#
# Usage:
#   make dab-validate BUNDLE=recommendation_engine DAB_TARGET=dev-sp
#   make dab-deploy   BUNDLE=inventory_optimization DAB_TARGET=test-sp
#   make dab-destroy  BUNDLE=document_intelligence DAB_TARGET=dev-sp
#   make dab-run      BUNDLE=document_intelligence RUN_JOB=document_intelligence_pipeline_job DAB_TARGET=prod-sp
#
# dab-destroy runs `databricks bundle destroy` (removes deployed jobs, pipelines, apps, etc. for that bundle
# + target). Default: interactive confirm. For CI/non-interactive: DAB_DESTROY_AUTO_APPROVE=1

DAB_TARGET ?= dev-sp
DAB_PROFILE ?= $(DAB_TARGET)
BUNDLE ?=
RUN_JOB ?=
DAB_DESTROY_AUTO_APPROVE ?=

define dab_bundle_dir
# Deprecated: BUNDLE_DIR mapping is handled directly in dab-validate/dab-deploy/dab-destroy/dab-run.
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
$(if $(filter recommendation_engine,$(1)),recommendation_engine_build_training_base recommendation_engine_item_similarity_retrain recommendation_engine_als_retrain recommendation_engine_lightfm_retrain recommendation_engine_ranker_retrain recommendation_engine_retrain recommendation_engine_item_similarity_apply recommendation_engine_als_apply recommendation_engine_lightfm_apply recommendation_engine_ranker_apply recommendation_engine_apply,\
$(if $(filter inventory_optimization,$(1)),inventory_demand_forecasting_retrain inventory_writeoff_risk_retrain inventory_replenishment_retrain inventory_demand_forecasting_apply inventory_writeoff_risk_apply inventory_replenishment_apply,\
$(if $(filter document_intelligence,$(1)),document_intelligence_generate_job document_intelligence_pipeline_job,\
)))
endef

# Some resources (Genie spaces and UC foundation) require direct deploy engine.
define dab_requires_direct_engine
$(if $(filter uc_foundation ai_powered_insights_genie_spaces,$(1)),1,)
endef

dab-workspace-print:
	@echo "$(WORKSPACE_BUNDLE_PREFIX)   (WORKSPACE_USER_EMAIL=$(WORKSPACE_USER_EMAIL))"
	@echo "Bundle workspace home defaults: /Workspace/Users/$(WORKSPACE_USER_EMAIL)"
	@echo "Override per deploy: databricks bundle deploy --var workspace_bundle_root=/Workspace/Users/you@co.com ..."
	@echo "Override deploying user in permissions: --var bundle_deploying_user_name=you@co.com"

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

dab-destroy:
	@test -n "$(strip $(BUNDLE))" || (echo "Usage: make dab-destroy BUNDLE=<bundle-name> [DAB_TARGET=...] [DAB_DESTROY_AUTO_APPROVE=1]" && exit 1)
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
	APPROVE=""; \
	if [ "$(DAB_DESTROY_AUTO_APPROVE)" = "1" ]; then APPROVE="--auto-approve"; fi; \
	echo "[dab-destroy] bundle=$(BUNDLE) dir=$$BUNDLE_DIR target=$(DAB_TARGET) profile=$(DAB_PROFILE)"; \
	if [ "$(call dab_requires_direct_engine,$(BUNDLE))" = "1" ]; then \
	  cd "$$BUNDLE_DIR" && DATABRICKS_BUNDLE_ENGINE=direct databricks bundle destroy $$APPROVE --target $(DAB_TARGET) --profile $(DAB_PROFILE); \
	else \
	  cd "$$BUNDLE_DIR" && databricks bundle destroy $$APPROVE --target $(DAB_TARGET) --profile $(DAB_PROFILE); \
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

dab-destroy-recommendation_engine:
	@$(MAKE) dab-destroy BUNDLE=recommendation_engine_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)
	@$(MAKE) dab-destroy BUNDLE=recommendation_engine_serving DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)
	@$(MAKE) dab-destroy BUNDLE=recommendation_engine DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

dab-run-recommendation_engine:
	@test -n "$(strip $(RUN_JOB))" || (echo "Usage: make dab-run-recommendation_engine RUN_JOB=<job-name> [DAB_TARGET=...]" && exit 1)
	@$(MAKE) dab-run BUNDLE=recommendation_engine RUN_JOB=$(RUN_JOB) DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-validate-inventory_optimization:
	@$(MAKE) dab-validate BUNDLE=inventory_optimization DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-deploy-inventory_optimization:
	@$(MAKE) dab-deploy BUNDLE=inventory_optimization DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-destroy-inventory_optimization:
	@$(MAKE) dab-destroy BUNDLE=inventory_optimization DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

dab-run-inventory_optimization:
	@test -n "$(strip $(RUN_JOB))" || (echo "Usage: make dab-run-inventory_optimization RUN_JOB=<job-name> [DAB_TARGET=...]" && exit 1)
	@$(MAKE) dab-run BUNDLE=inventory_optimization RUN_JOB=$(RUN_JOB) DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-validate-document_intelligence:
	@$(MAKE) dab-validate BUNDLE=document_intelligence DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-validate BUNDLE=document_intelligence_annotator_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-deploy-document_intelligence:
	@$(MAKE) dab-deploy BUNDLE=document_intelligence DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)
	@$(MAKE) dab-deploy BUNDLE=document_intelligence_annotator_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-destroy-document_intelligence:
	@$(MAKE) dab-destroy BUNDLE=document_intelligence_annotator_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)
	@$(MAKE) dab-destroy BUNDLE=document_intelligence DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

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

dab-destroy-ai_powered_insights:
	@$(MAKE) dab-destroy BUNDLE=ai_powered_insights_genie_spaces DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)
	@$(MAKE) dab-destroy BUNDLE=ai_powered_insights_dashboards DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)
	@$(MAKE) dab-destroy BUNDLE=ai_powered_insights_app DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

# --- Foundation/data DAB wrappers (shared) ---

dab-validate-uc_foundation:
	@$(MAKE) dab-validate BUNDLE=uc_foundation DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-deploy-uc_foundation:
	@$(MAKE) dab-deploy BUNDLE=uc_foundation DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-destroy-uc_foundation:
	@$(MAKE) dab-destroy BUNDLE=uc_foundation DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

dab-validate-healthcare_data_generator:
	@$(MAKE) dab-validate BUNDLE=healthcare_data_generator DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-deploy-healthcare_data_generator:
	@$(MAKE) dab-deploy BUNDLE=healthcare_data_generator DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-destroy-healthcare_data_generator:
	@$(MAKE) dab-destroy BUNDLE=healthcare_data_generator DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

dab-run-healthcare_data_generator:
	@$(MAKE) dab-run BUNDLE=healthcare_data_generator DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-validate-healthcare_data_medallion:
	@$(MAKE) dab-validate BUNDLE=healthcare_data_medallion DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-deploy-healthcare_data_medallion:
	@$(MAKE) dab-deploy BUNDLE=healthcare_data_medallion DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

dab-destroy-healthcare_data_medallion:
	@$(MAKE) dab-destroy BUNDLE=healthcare_data_medallion DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE) DAB_DESTROY_AUTO_APPROVE=$(DAB_DESTROY_AUTO_APPROVE)

dab-run-healthcare_data_medallion:
	@$(MAKE) dab-run BUNDLE=healthcare_data_medallion DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

# --- Consistent "reco" naming for reco DAB bundle set ---

dab-validate-reco: dab-validate-recommendation_engine

dab-deploy-reco: dab-deploy-recommendation_engine

dab-destroy-reco: dab-destroy-recommendation_engine

dab-run-reco:
	@test -n "$(strip $(RUN_JOB))" || (echo "Usage: make dab-run-reco RUN_JOB=<job-name> [DAB_TARGET=...]" && exit 1)
	@$(MAKE) dab-run-recommendation_engine RUN_JOB=$(RUN_JOB) DAB_TARGET=$(DAB_TARGET) DAB_PROFILE=$(DAB_PROFILE)

# Optional convenience: keep your old UC foundation deploy target name,
# but route it through dab-deploy to reuse the bundle framework.
uc-foundation-deploy-dab-wrapper:
	@$(MAKE) dab-deploy BUNDLE=uc_foundation DAB_TARGET=$(UC_FOUNDATION_TARGET) DAB_PROFILE=$(UC_FOUNDATION_TARGET)
