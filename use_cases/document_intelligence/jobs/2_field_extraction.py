"""
Job-style entrypoint for field extraction / structuring.

Intended for:
- Local runs: python use_cases/document_intelligence/jobs/2_field_extraction.py
- Databricks jobs: spark_python_task.python_file pointing here.
"""

from loguru import logger

from use_cases.document_intelligence.config import get_config
from use_cases.document_intelligence.ner_field_extraction import run_field_extraction


def main() -> dict:
    cfg = get_config()
    logger.info(
        "doc-intel field extraction: labels_dir={}, annotated_dir={}, on_databricks={}",
        cfg["labels_dir"],
        cfg["annotated_dir"],
        cfg["on_databricks"],
    )
    df = run_field_extraction(cfg)
    summary = {
        "n_documents": int(df["doc_id"].nunique() if not df.empty else 0),
        "n_rows": int(len(df)),
    }
    logger.info("doc-intel field extraction summary: {}", summary)
    return summary


if __name__ == "__main__":
    result = main()
    logger.info("doc-intel field extraction run done: {}", result)
