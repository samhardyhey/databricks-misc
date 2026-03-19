"""
Read/write predictions for document intelligence.

When ``config["data_source"] == "local"``:
- OCR → ``predictions_dir/ocr/`` (JSON per doc)
- fields → ``predictions_dir/fields/`` (JSON per doc)

When ``data_source == "catalog"`` (Databricks + UC): the same logical rows are written with
``_write_catalog_table`` to ``<catalog_schema>.<table_doc_pages>`` and
``<catalog_schema>.<table_doc_fields_extracted>``.
"""

import json
from pathlib import Path

import pandas as pd
from loguru import logger


def _write_catalog_table(config: dict, df: pd.DataFrame, table_name: str) -> None:
    """Write a pandas DataFrame to a Unity Catalog table when running on Databricks."""
    if df.empty:
        return
    try:
        from pyspark.sql import SparkSession
    except Exception as e:  # noqa: BLE001
        logger.warning("Catalog write skipped (pyspark unavailable): {}", e)
        return

    spark = SparkSession.builder.getOrCreate()
    full_table = f"{config['catalog_schema']}.{table_name}"
    spark_df = spark.createDataFrame(df)
    spark_df.write.mode("overwrite").saveAsTable(full_table)
    logger.info("Wrote {} rows to {}", len(df), full_table)


def write_ocr_output(config: dict, ocr_df: pd.DataFrame) -> None:
    """
    Persist OCR rows: catalog → UC table ``table_doc_pages``; local → one JSON per doc under
    ``predictions_dir/ocr/`` with ``{ "doc_id", "pages": [ {"page", "text"}, ... ] }``.
    """
    if ocr_df.empty:
        return
    if config.get("data_source") == "catalog":
        _write_catalog_table(config, ocr_df, config["table_doc_pages"])
        return
    out_dir: Path = config["predictions_dir"] / "ocr"
    out_dir.mkdir(parents=True, exist_ok=True)
    for doc_id, grp in ocr_df.groupby("doc_id"):
        pages = [
            {"page": int(r["page"]), "text": str(r["text"])}
            for _, r in grp.sort_values("page").iterrows()
        ]
        path = out_dir / f"{doc_id}.json"
        with path.open("w") as f:
            json.dump({"doc_id": doc_id, "pages": pages}, f, indent=2)
    logger.info("Wrote {} OCR JSONs to {}", ocr_df["doc_id"].nunique(), out_dir)


def _row_to_nested(row: pd.Series) -> dict:
    """Convert flat field-extraction row to nested JSON for annotator."""
    return {
        "prescription_number": _str(row.get("prescription_number")),
        "prescription_date": _str(row.get("prescription_date")),
        "expiry_date": _str(row.get("expiry_date")),
        "patient": {
            "name": _str(row.get("patient_name")),
            "date_of_birth": _str(row.get("patient_date_of_birth")),
            "address": _str(row.get("patient_address")),
            "medicare_number": _str(row.get("patient_medicare_number")),
            "phone": _str(row.get("patient_phone")),
        },
        "doctor": {
            "name": _str(row.get("doctor_name")),
            "provider_number": _str(row.get("doctor_provider_number")),
            "ahpra_number": _str(row.get("doctor_ahpra_number")),
            "signature_date": _str(row.get("doctor_signature_date")),
        },
        "facility": {
            "name": _str(row.get("facility_name")),
            "address": _str(row.get("facility_address")),
            "phone": _str(row.get("facility_phone")),
            "abn": _str(row.get("facility_abn")),
        },
        "medication": {
            "name": _str(row.get("medication_name")),
            "dosage_form": _str(row.get("medication_dosage_form")),
            "strength": _str(row.get("medication_strength")),
            "quantity": _str(row.get("medication_quantity")),
            "frequency": _str(row.get("medication_frequency")),
            "duration": _str(row.get("medication_duration")),
            "instructions": _str(row.get("medication_instructions")),
            "repeats": _str(row.get("medication_repeats")),
        },
    }


def _str(v: object) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


def write_field_output(config: dict, fields_df: pd.DataFrame) -> None:
    """
    Persist field-extraction rows: catalog → UC ``table_doc_fields_extracted``; local → one nested
    JSON per doc under ``predictions_dir/fields/`` (annotator-friendly schema).
    """
    if fields_df.empty:
        return
    if config.get("data_source") == "catalog":
        _write_catalog_table(config, fields_df, config["table_doc_fields_extracted"])
        return
    out_dir: Path = config["predictions_dir"] / "fields"
    out_dir.mkdir(parents=True, exist_ok=True)
    for _, row in fields_df.iterrows():
        doc_id = row.get("doc_id")
        if doc_id is None or (isinstance(doc_id, float) and pd.isna(doc_id)):
            continue
        path = out_dir / f"{doc_id}.json"
        with path.open("w") as f:
            json.dump(_row_to_nested(row), f, indent=2)
    logger.info("Wrote {} field JSONs to {}", len(fields_df), out_dir)
