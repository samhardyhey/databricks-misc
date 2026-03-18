"""
Configuration for the Prescription PDF Annotator (review predictions).

Aligns with the document intelligence pipeline: same base dir (DOCINT_BASE_DIR).
- Read only from predictions/fields/ (OCR + NER pipeline output to verify/correct).
- Save corrections to annotated/labels/. No ground-truth labels — prediction-only.
"""

import os
from pathlib import Path

# Repo root for default base dir (annotator/config.py -> parents[3] = repo root)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BASE_DIR = _REPO_ROOT / "data" / "local" / "prescription_pdfs"


def get_base_dir() -> Path:
    """Base directory (documents/, predictions/, annotated/). Override with DOCINT_BASE_DIR or LOCAL_DATA_PATH."""
    p = os.environ.get("DOCINT_BASE_DIR") or os.environ.get(
        "LOCAL_DATA_PATH", str(_DEFAULT_BASE_DIR)
    )
    return Path(p).resolve()


BASE_DIR = get_base_dir()

# Directory containing PDF documents
DOCUMENTS_DIR = BASE_DIR / "documents"

# Predictions from pipeline (OCR + field extraction) — only source for review
PREDICTIONS_FIELDS_DIR = BASE_DIR / "predictions" / "fields"

# Where corrected annotations are saved
ANNOTATED_DIR = BASE_DIR / "annotated"
