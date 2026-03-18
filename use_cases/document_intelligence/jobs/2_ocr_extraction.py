"""
Job-style entrypoint for OCR / text extraction.

Intended for:
- Local runs: python use_cases/document_intelligence/jobs/2_ocr_extraction.py
- Databricks jobs: spark_python_task.python_file pointing here.
"""

from loguru import logger

from use_cases.document_intelligence.config import get_config
from use_cases.document_intelligence.ocr_pipeline import run_ocr


def main() -> dict:
    cfg = get_config()
    logger.info(
        "doc-intel OCR: base_dir={}, documents_dir={}, on_databricks={}",
        cfg["base_dir"],
        cfg["documents_dir"],
        cfg["on_databricks"],
    )
    df = run_ocr(cfg)
    summary = {
        "n_documents": int(df["doc_id"].nunique() if not df.empty else 0),
        "n_rows": int(len(df)),
    }
    logger.info("doc-intel OCR summary: {}", summary)
    return summary


if __name__ == "__main__":
    result = main()
    logger.info("doc-intel OCR run done: {}", result)
