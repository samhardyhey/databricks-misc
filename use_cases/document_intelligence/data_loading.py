"""
Data loading helpers for the document intelligence use case.

Pattern is aligned with other use cases (recommendation_engine, inventory_optimization):
- Single `load_document_data(config)` entrypoint.
- Config is provided by `use_cases.document_intelligence.config.get_config()`.
"""

from pathlib import Path
from typing import Any

from loguru import logger


def load_document_data(config: dict) -> dict[str, Any]:
    """
    Discover available prescription PDFs and labels based on config.

    Returns a dict with:
    - base_dir: Path
    - documents_dir: Path
    - labels_dir: Path
    - annotated_labels_dir: Path (may not exist)
    - pdf_files: list[Path]
    - label_files: list[Path]
    - annotated_label_files: list[Path]
    """
    base_dir: Path = config["base_dir"]
    documents_dir: Path = config["documents_dir"]
    labels_dir: Path = config["labels_dir"]
    annotated_labels_dir: Path = config["annotated_dir"] / "labels"

    pdf_files = sorted(documents_dir.glob("*.pdf")) if documents_dir.exists() else []
    label_files = sorted(labels_dir.glob("*.json")) if labels_dir.exists() else []
    annotated_label_files = (
        sorted(annotated_labels_dir.glob("*.json"))
        if annotated_labels_dir.exists()
        else []
    )

    logger.info(
        "Document data: base_dir={}, pdfs={}, labels={}, annotated_labels={}",
        base_dir,
        len(pdf_files),
        len(label_files),
        len(annotated_label_files),
    )

    return {
        "base_dir": base_dir,
        "documents_dir": documents_dir,
        "labels_dir": labels_dir,
        "annotated_labels_dir": annotated_labels_dir,
        "pdf_files": pdf_files,
        "label_files": label_files,
        "annotated_label_files": annotated_label_files,
    }
