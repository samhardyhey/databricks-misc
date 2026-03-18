"""
Data loading for document intelligence: local file paths vs UC volume + tables.

- Local: discover PDFs under documents_dir, prediction files under predictions_dir.
- Catalog: list documents from UC managed volume; prediction counts from UC tables (requires Spark).
"""

from pathlib import Path
from typing import Any

from loguru import logger


def _load_document_data_local(config: dict) -> dict[str, Any]:
    """Discover PDFs and prediction paths under base_dir (local only)."""
    base_dir: Path = config["base_dir"]
    documents_dir: Path = config["documents_dir"]
    predictions_dir: Path = config["predictions_dir"]
    ocr_dir = predictions_dir / "ocr"
    fields_dir = predictions_dir / "fields"
    annotated_dir = config["annotated_dir"] / "labels"

    pdf_files = sorted(documents_dir.glob("*.pdf")) if documents_dir.exists() else []
    ocr_files = sorted(ocr_dir.glob("*.json")) if ocr_dir.exists() else []
    field_files = sorted(fields_dir.glob("*.json")) if fields_dir.exists() else []
    annotated_files = (
        sorted(annotated_dir.glob("*.json")) if annotated_dir.exists() else []
    )

    logger.info(
        "Document data (local): base_dir={}, pdfs={}, ocr={}, fields={}, annotated={}",
        base_dir,
        len(pdf_files),
        len(ocr_files),
        len(field_files),
        len(annotated_files),
    )

    return {
        "data_source": "local",
        "base_dir": base_dir,
        "documents_dir": documents_dir,
        "predictions_dir": predictions_dir,
        "pdf_files": pdf_files,
        "ocr_files": ocr_files,
        "field_files": field_files,
        "annotated_label_files": annotated_files,
    }


def _load_document_data_catalog(config: dict, spark: Any = None) -> dict[str, Any]:
    """
    Return catalog config and optional table row counts (no volume listing here).
    Jobs that read/write volume or tables do so explicitly with config keys.
    """
    if spark is None and config.get("on_databricks"):
        try:
            from pyspark.sql import SparkSession

            spark = SparkSession.builder.getOrCreate()
        except Exception as e:
            logger.warning("Catalog path: Spark not available: {}", e)

    volume_path = config["documents_volume_path"]
    catalog_schema = config["catalog_schema"]
    table_pages = config["table_doc_pages"]
    table_fields = config["table_doc_fields_extracted"]
    full_table_pages = f"{catalog_schema}.{table_pages}"
    full_table_fields = f"{catalog_schema}.{table_fields}"

    ocr_count = 0
    fields_count = 0
    if spark is not None:
        try:
            ocr_count = spark.table(full_table_pages).count()
        except Exception:
            pass
        try:
            fields_count = spark.table(full_table_fields).count()
        except Exception:
            pass

    logger.info(
        "Document data (catalog): volume={}, {}={} rows, {}={} rows",
        volume_path,
        full_table_pages,
        ocr_count,
        full_table_fields,
        fields_count,
    )

    return {
        "data_source": "catalog",
        "pdf_files": [],
        "pdf_paths": [],
        "ocr_count": ocr_count,
        "fields_count": fields_count,
        "documents_volume_path": volume_path,
        "catalog_schema": catalog_schema,
        "table_doc_pages": table_pages,
        "table_doc_fields_extracted": table_fields,
        "spark": spark,
    }


def load_document_data(config: dict, spark: Any = None) -> dict[str, Any]:
    """
    Discover documents and prediction locations from config.
    Local: file paths under base_dir. Catalog: UC volume + table names (requires Spark).
    """
    if config["data_source"] == "catalog":
        return _load_document_data_catalog(config, spark=spark)
    return _load_document_data_local(config)
