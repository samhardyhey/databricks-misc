# Repo root (directory containing this Makefile). Run `make` from repo root.
REPO_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(patsubst %/,%,$(REPO_ROOT))

# Source root: repo root. All internal imports are from root (e.g. data.*, use_cases.*).
# After `make install`, the UV venv's editable install provides this; otherwise set PYTHONPATH.
export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

# Prefer venv python if .venv exists
VENV_PY := $(REPO_ROOT)/.venv/bin/python
PY ?= $(if $(wildcard $(VENV_PY)),$(VENV_PY),python3)

# Prescription PDF generation: sensible defaults (override: make document_intelligence-generate-pdfs DOC_INTEL_PDF_ARGS="-n 5 -s 42")
DOC_INTEL_PDF_ARGS ?= -n 10
DOC_INTEL_PDF_OUTPUT := use_cases/document_intelligence/prescription_pdfs

.PHONY: help cleanup format document_intelligence-generate-pdfs
.PHONY: uv-venv uv-sync install uv-dev uv-activate

help:
	@echo "Targets:"
	@echo "  make uv-venv              - Create .venv (UV environment)"
	@echo "  make uv-sync / install     - Install deps (uv sync); use install for dev deps: make install uv-dev"
	@echo "  make uv-dev               - Install dev deps (autoflake8, isort, black)"
	@echo "  make uv-activate          - Print activate command for .venv"
	@echo "  make cleanup              - Remove __pycache__, .pyc, .pytest_cache, .coverage, etc."
	@echo "  make format [FMT_ARGS=.]  - Run autoflake8, isort, black"
	@echo "  make document_intelligence-generate-pdfs [DOC_INTEL_PDF_ARGS=-n 10]  - Generate prescription PDFs under use_cases/document_intelligence"

# --- UV environment (databricks-misc) ---
uv-venv:
	cd $(REPO_ROOT) && uv venv
	@echo "Created .venv. Next: make install  [make uv-dev for format tools]"

uv-sync:
	cd $(REPO_ROOT) && uv sync
	@echo "Synced dependencies. For dev tools (autoflake8, isort, black): make uv-dev"

install: uv-sync

uv-dev:
	cd $(REPO_ROOT) && uv sync --extra dev
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

# --- Format (autoflake8 -> isort -> black) ---
FMT_ARGS ?= data use_cases
format:
	autoflake8 $(FMT_ARGS) --remove-all-unused-imports --remove-unused-variables --recursive --in-place
	isort $(FMT_ARGS)
	black $(FMT_ARGS)
	@echo "Format done."

# --- Run local scripts (repo root = source root; use data.* / use_cases.* imports) ---
document_intelligence-generate-pdfs:
	cd $(REPO_ROOT) && $(PY) data/prescription_pdf_generator/generate_prescription_pdfs_local.py \
		-o $(DOC_INTEL_PDF_OUTPUT) \
		$(DOC_INTEL_PDF_ARGS)
	@echo "Generated PDFs in $(DOC_INTEL_PDF_OUTPUT)/"
