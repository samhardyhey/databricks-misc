"""
Lightweight OCR / text extraction pipeline for prescription PDFs.

Current behaviour (MVP):
- Iterate over PDFs under config["documents_dir"]
- Use pdfplumber (if installed) to extract page text; otherwise fall back to an
  empty DataFrame with a warning so the rest of the pipeline can still run.

This is intentionally simple and local-first; the same code can run on
Databricks as a standard Python library dependency (no Spark OCR/NLP).
"""

from pathlib import Path
from typing import Iterable

import pandas as pd
from loguru import logger


def _iter_pdfs(documents_dir: Path) -> Iterable[Path]:
    if not documents_dir.exists():
        logger.warning("Documents directory does not exist: {}", documents_dir)
        return []
    pdfs = sorted(documents_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning("No PDFs found in documents directory: {}", documents_dir)
    return pdfs


def run_ocr(config: dict) -> pd.DataFrame:
    """
    Extract per-page text for all PDFs in documents_dir.

    Returns a DataFrame with columns:
    - doc_id: stem of the PDF filename
    - page: 1-based page number
    - text: extracted text (may be empty if OCR/lib missing)
    """
    documents_dir: Path = config["documents_dir"]
    rows: list[dict] = []

    try:
        import pdfplumber  # type: ignore[import]
    except ImportError:
        logger.warning(
            "pdfplumber is not installed; OCR step will be skipped. "
            "Install pdfplumber in your environment to enable text extraction."
        )
        return pd.DataFrame(columns=["doc_id", "page", "text"])

    for pdf_path in _iter_pdfs(documents_dir):
        doc_id = pdf_path.stem
        logger.debug("Running OCR/text extraction for {}", pdf_path)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    rows.append({"doc_id": doc_id, "page": i, "text": text})
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to process {}: {}", pdf_path, exc)

    df = pd.DataFrame(rows, columns=["doc_id", "page", "text"])
    logger.info(
        "OCR extracted {} rows from {} documents", len(df), df["doc_id"].nunique()
    )
    if config.get("data_source") == "local" and not df.empty:
        from use_cases.document_intelligence.predictions_io import write_ocr_output

        write_ocr_output(config, df)
    return df
