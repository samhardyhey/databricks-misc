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

# Prescription PDF generation: sensible defaults (override: make data-local-generate-pdfs DOC_INTEL_PDF_ARGS="-n 5 -s 42")
DOC_INTEL_PDF_ARGS ?= -n 10
DOC_INTEL_PDF_OUTPUT := use_cases/document_intelligence/prescription_pdfs

# Marvelous MLOps: separate requirements, use sub-venv (make marvelous_mlops-venv first)
MARVELOUS_MLOPS_DIR := $(REPO_ROOT)/marvelous_mlops
MARVELOUS_PY := $(MARVELOUS_MLOPS_DIR)/.venv/bin/python

.PHONY: help cleanup format document_intelligence-generate-pdfs
.PHONY: data-local-generate data-local-generate-quick data-local-generate-pdfs data-local-dbt-run
.PHONY: marvelous_mlops-venv marvelous_mlops-fetch-medium marvelous_mlops-fetch-substack marvelous_mlops-fetch-youtube
.PHONY: uv-venv uv-sync install uv-dev uv-activate

help:
	@echo "Targets:"
	@echo "  make uv-venv              - Create .venv (uses uv if available, else python3 -m venv)"
	@echo "  make uv-sync / install     - Install deps; use install then uv-dev for dev tools"
	@echo "  make uv-dev               - Install dev deps (autoflake, isort, black)"
	@echo "  make uv-activate          - Print activate command for .venv"
	@echo "  make cleanup              - Remove __pycache__, .pyc, .pytest_cache, .coverage, etc."
	@echo "  make format [FMT_ARGS=.]  - Run autoflake, isort, black"
	@echo ""
	@echo "  Local (data generation / medallion):"
	@echo "  make data-local-generate        - Generate healthcare CSVs to data/local/ (default sizes)"
	@echo "  make data-local-generate-quick  - Generate healthcare CSVs to data/local/ (small sizes)"
	@echo "  make data-local-generate-pdfs   - Generate prescription PDFs (use_cases/document_intelligence/prescription_pdfs)"
	@echo "  make data-local-dbt-run         - Run medallion dbt locally (requires DuckDB profile + raw data in data/local/)"
	@echo ""
	@echo "  make document_intelligence-generate-pdfs  - Alias for data-local-generate-pdfs [DOC_INTEL_PDF_ARGS=-n 10]"
	@echo ""
	@echo "  Marvelous MLOps (separate venv; run marvelous_mlops-venv first):"
	@echo "  make marvelous_mlops-venv             - Create .venv and install requirements in marvelous_mlops/"
	@echo "  make marvelous_mlops-fetch-medium      - Fetch Medium articles"
	@echo "  make marvelous_mlops-fetch-substack   - Fetch Substack posts"
	@echo "  make marvelous_mlops-fetch-youtube    - Fetch YouTube transcripts"

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

# --- Cleanup ---
cleanup:
	find $(REPO_ROOT) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find $(REPO_ROOT) -type f -name "*.pyc" -delete 2>/dev/null || true
	find $(REPO_ROOT) -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf $(REPO_ROOT)/.pytest_cache $(REPO_ROOT)/.coverage $(REPO_ROOT)/.mypy_cache 2>/dev/null || true
	@echo "Cleanup done."

# --- Format (autoflake -> isort -> black); requires make uv-dev ---
FMT_ARGS ?= data use_cases
format:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make uv-dev" && exit 1)
	cd $(REPO_ROOT) && $(PY) -m autoflake $(FMT_ARGS) --remove-all-unused-imports --remove-unused-variables --recursive --in-place
	cd $(REPO_ROOT) && $(PY) -m isort $(FMT_ARGS)
	cd $(REPO_ROOT) && $(PY) -m black $(FMT_ARGS)
	@echo "Format done."

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
	cd $(REPO_ROOT) && $(PY) data/prescription_pdf_generator/generate_prescription_pdfs_local.py \
		-o $(DOC_INTEL_PDF_OUTPUT) \
		$(DOC_INTEL_PDF_ARGS)
	@echo "Generated PDFs in $(DOC_INTEL_PDF_OUTPUT)/"

data-local-dbt-run:
	@test -d $(MEDALLION_DIR) || (echo "Medallion dir missing: $(MEDALLION_DIR)" && exit 1)
	@test -x $(DBT_BIN) || (echo "dbt not found. Run: make install-dbt" && exit 1)
	cd $(MEDALLION_DIR) && DBT_PROFILES_DIR=$(MEDALLION_DIR)/dbt_profiles DBT_DUCKDB_PATH=$(REPO_ROOT)/data/local/medallion.duckdb $(DBT_BIN) run --profile duckdb
	@echo "dbt run (duckdb) done."

document_intelligence-generate-pdfs: data-local-generate-pdfs

install-dbt:
	@test -x $(VENV_PY) || (echo "Run: make uv-venv && make install" && exit 1)
	cd $(REPO_ROOT) && $(PY) -m pip install "dbt-duckdb>=1.9.0"
	@echo "dbt-duckdb installed. You can run: make data-local-dbt-run (after setting up DuckDB profile + raw data)."

# --- Marvelous MLOps (sub-usecase: own venv and requirements.txt) ---
marvelous_mlops-venv:
	cd $(MARVELOUS_MLOPS_DIR) && (command -v uv >/dev/null 2>&1 && uv venv || python3 -m venv .venv) && .venv/bin/pip install -r requirements.txt
	@echo "marvelous_mlops .venv ready. Run: make marvelous_mlops-fetch-medium|fetch-substack|fetch-youtube"

marvelous_mlops-fetch-medium:
	@test -x $(MARVELOUS_PY) || (echo "Run: make marvelous_mlops-venv" && exit 1)
	cd $(MARVELOUS_MLOPS_DIR) && $(MARVELOUS_PY) fetch_medium.py
	@echo "Medium fetch done."

marvelous_mlops-fetch-substack:
	@test -x $(MARVELOUS_PY) || (echo "Run: make marvelous_mlops-venv" && exit 1)
	cd $(MARVELOUS_MLOPS_DIR) && $(MARVELOUS_PY) fetch_substack.py
	@echo "Substack fetch done."

marvelous_mlops-fetch-youtube:
	@test -x $(MARVELOUS_PY) || (echo "Run: make marvelous_mlops-venv" && exit 1)
	cd $(MARVELOUS_MLOPS_DIR) && $(MARVELOUS_PY) fetch_youtube.py
	@echo "YouTube fetch done."
