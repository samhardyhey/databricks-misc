"""
Configuration for the Prescription PDF Annotator (review predictions).

Aligns with the document intelligence pipeline: same base dir (DOCINT_BASE_DIR).
- Read only from predictions/fields/ (OCR + NER pipeline output to verify/correct).
- Save corrections to annotated/labels/. No ground-truth labels — prediction-only.
"""

from pathlib import Path

from use_cases.document_intelligence.config import get_local_base_dir


def get_base_dir() -> Path:
    """Same as document_intelligence.get_local_base_dir; kept for annotator callers."""
    return get_local_base_dir()


BASE_DIR = get_base_dir()

# Directory containing PDF documents
DOCUMENTS_DIR = BASE_DIR / "documents"

# Predictions from pipeline (OCR + field extraction) — only source for review
PREDICTIONS_FIELDS_DIR = BASE_DIR / "predictions" / "fields"

# Where corrected annotations are saved
ANNOTATED_DIR = BASE_DIR / "annotated"
