"""
Field extraction / structuring for prescription documents.

MVP behaviour:
- Load JSON labels from config["labels_dir"] (ground truth) or config["annotated_dir"]
  when present.
- Flatten them into a tabular structure that mirrors the target gold_doc_labels schema.

Later this module can be extended with actual NER / parsing models that read from
OCR output and write predicted fields; the interface (run_field_extraction) stays
the same so jobs and orchestration do not change.
"""

import json
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
    Build a tabular view of prescription fields from labels/annotations.

    Prefers annotated_dir (if it exists and has labels/) and falls back to
    labels_dir (generator output).
    """
    labels_dir: Path = config["labels_dir"]
    annotated_dir: Path = config["annotated_dir"] / "labels"

    source_dir = annotated_dir if annotated_dir.exists() else labels_dir
    if source_dir == annotated_dir:
        logger.info("Using annotated labels from {}", annotated_dir)
    else:
        logger.info("Using generator labels from {}", labels_dir)

    raw_rows = _load_labels_dir(source_dir)
    flat_rows = [_flatten_label(r["doc_id"], r["raw"]) for r in raw_rows]
    df = pd.DataFrame(flat_rows)
    logger.info(
        "Built field extraction table with {} rows and {} columns",
        len(df),
        len(df.columns),
    )
    if config.get("data_source") == "local" and not df.empty:
        from use_cases.document_intelligence.predictions_io import write_field_output

        write_field_output(config, df)
    return df
