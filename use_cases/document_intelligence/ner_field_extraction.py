"""
Field extraction / structuring for prescription documents.

1. **OCR + spaCy (preferred in ``auto``)** — When ``predictions/ocr/*.json`` exists and
   spaCy is installed, run ``spacy_ner_pipeline.extract_fields_from_ocr`` (pretrained
   ``en_core_web_sm`` NER + AU-style regex helpers). No trained model in-repo; this is
   *apply* only.

2. **Labels fallback** — Load JSON labels from ``labels_dir`` / ``annotated_dir`` for
   demos or when OCR/spaCy is unavailable.

``DOCINT_FIELD_SOURCE``: ``auto`` (default) | ``ocr`` | ``labels``.
"""

import json
import os
from pathlib import Path

import pandas as pd
from loguru import logger


def _load_labels_dir(labels_dir: Path) -> list[dict]:
    if not labels_dir.exists():
        logger.warning("Labels directory does not exist: {}", labels_dir)
        return []
    rows: list[dict] = []
    for path in sorted(labels_dir.glob("*.json")):
        try:
            with path.open("r") as f:
                data = json.load(f)
            rows.append({"doc_id": path.stem, "raw": data})
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load JSON label {}: {}", path, exc)
    return rows


def _flatten_label(doc_id: str, data: dict) -> dict:
    patient = data.get("patient", {}) or {}
    doctor = data.get("doctor", {}) or {}
    facility = data.get("facility", {}) or {}
    medication = data.get("medication", {}) or {}

    return {
        "doc_id": doc_id,
        "prescription_number": data.get("prescription_number"),
        "prescription_date": data.get("prescription_date"),
        "expiry_date": data.get("expiry_date"),
        "patient_name": patient.get("name"),
        "patient_date_of_birth": patient.get("date_of_birth"),
        "patient_address": patient.get("address"),
        "patient_medicare_number": patient.get("medicare_number"),
        "patient_phone": patient.get("phone"),
        "doctor_name": doctor.get("name"),
        "doctor_provider_number": doctor.get("provider_number"),
        "doctor_ahpra_number": doctor.get("ahpra_number"),
        "doctor_signature_date": doctor.get("signature_date"),
        "facility_name": facility.get("name"),
        "facility_address": facility.get("address"),
        "facility_phone": facility.get("phone"),
        "facility_abn": facility.get("abn"),
        "medication_name": medication.get("name"),
        "medication_dosage_form": medication.get("dosage_form"),
        "medication_strength": medication.get("strength"),
        "medication_quantity": medication.get("quantity"),
        "medication_frequency": medication.get("frequency"),
        "medication_duration": medication.get("duration"),
        "medication_instructions": medication.get("instructions"),
        "medication_repeats": medication.get("repeats"),
    }


def run_field_extraction(config: dict) -> pd.DataFrame:
    """
    Build a tabular view of prescription fields: spaCy+rules on OCR when configured,
    else JSON labels.
    """
    mode = os.environ.get("DOCINT_FIELD_SOURCE", "auto").strip().lower()

    if mode in ("auto", "ocr"):
        from use_cases.document_intelligence.spacy_ner_pipeline import (
            extract_fields_from_ocr,
        )

        spacy_df = extract_fields_from_ocr(config)
        if not spacy_df.empty:
            logger.info(
                "Field extraction via spaCy/rules on OCR ({} rows); DOCINT_FIELD_SOURCE={}",
                len(spacy_df),
                mode,
            )
            from use_cases.document_intelligence.predictions_io import (
                write_field_output,
            )

            write_field_output(
                config, spacy_df.drop(columns=["extraction_method"], errors="ignore")
            )
            return spacy_df.drop(columns=["extraction_method"], errors="ignore")
        if mode == "ocr":
            logger.warning(
                "DOCINT_FIELD_SOURCE=ocr but spaCy extraction produced no rows "
                "(install spaCy + en_core_web_sm, run OCR job first)."
            )
            return pd.DataFrame()

    labels_dir: Path = config["labels_dir"]
    annotated_dir: Path = config["annotated_dir"] / "labels"

    source_dir = annotated_dir if annotated_dir.exists() else labels_dir
    if source_dir == annotated_dir:
        logger.info("Using annotated labels from {}", annotated_dir)
    else:
        logger.info(
            "Using generator labels from {} (OCR/spaCy unavailable or empty; auto fallback)",
            labels_dir,
        )

    raw_rows = _load_labels_dir(source_dir)
    flat_rows = [_flatten_label(r["doc_id"], r["raw"]) for r in raw_rows]
    df = pd.DataFrame(flat_rows)
    logger.info(
        "Built field extraction table with {} rows and {} columns",
        len(df),
        len(df.columns),
    )
    if not df.empty:
        from use_cases.document_intelligence.predictions_io import write_field_output

        write_field_output(config, df)
    return df
