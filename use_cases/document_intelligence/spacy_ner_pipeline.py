"""
Apply spaCy + rule-based patterns to OCR text (prescription documents).

**No training or offline evaluation** in this repo path — we load a pretrained English
pipeline when available (`en_core_web_sm`) and enrich with `EntityRuler` regex patterns
for AU-style identifiers. If the vocabulary model is missing, fall back to `blank:en`
with ruler-only entities.

Install: ``uv sync --extra document_intelligence`` (pinned wheel) or at runtime
    ``ensure_spacy_model.ensure_en_core_web_sm()`` / ``python use_cases/document_intelligence/ensure_spacy_model.py``.
    See ``model_dep_urls.py`` and https://github.com/explosion/spacy-models#downloading-models
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger


# Rule labels (custom order for overlapping matches: longer/specific first).
_REGEX_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("MEDICARE_NUMBER", re.compile(r"\b\d{4}\s?\d{5}\s?\d?\b")),
    ("ABN", re.compile(r"\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b")),
    (
        "PHONE_AU",
        re.compile(r"\b(?:\+?61[\s-]?|0)[2-478](?:[\s-]?\d){8}\b"),
    ),
    (
        "AHPRA_NUMBER",
        re.compile(r"\b(?:AHPRA|Ahpra)[\s:]*#?\s*(\d{5,12})\b", re.IGNORECASE),
    ),
    ("PRESCRIPTION_NUMBER", re.compile(r"\b(?:Rx|RX|Prescription|Script)\s*#?\s*[:\-]?\s*([A-Z0-9\-]{4,})\b", re.I)),
    ("DATE_DMY", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
)


def _load_nlp() -> Any:
    import spacy
    from spacy.language import Language

    from use_cases.document_intelligence.ensure_spacy_model import ensure_en_core_web_sm

    nlp: Language
    if ensure_en_core_web_sm():
        nlp = spacy.load("en_core_web_sm")
    else:
        logger.warning(
            "en_core_web_sm unavailable after check/install; using blank English "
            "(regex-based fields only; no PERSON/ORG NER). "
            "Install manually: python use_cases/document_intelligence/ensure_spacy_model.py"
        )
        nlp = spacy.blank("en")
    return nlp


_NLP = None


def get_nlp():
    global _NLP
    if _NLP is None:
        _NLP = _load_nlp()
    return _NLP


def _regex_findall(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {label: [] for label, _ in _REGEX_RULES}
    for label, rx in _REGEX_RULES:
        for m in rx.finditer(text):
            out[label].append(m.group(1) if m.lastindex else m.group(0))
    return out


def _flatten_spacy_doc(text: str, nlp: Any) -> dict[str, Any]:
    rx_hits = _regex_findall(text)
    doc = nlp(text[:500_000] if len(text) > 500_000 else text)

    people: list[str] = []
    orgs: list[str] = []
    dates_spacy: list[str] = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            people.append(ent.text.strip())
        elif ent.label_ in ("ORG", "FAC"):
            orgs.append(ent.text.strip())
        elif ent.label_ == "DATE":
            dates_spacy.append(ent.text.strip())

    medicare = rx_hits["MEDICARE_NUMBER"]
    abn = rx_hits["ABN"]
    phone = rx_hits["PHONE_AU"]
    ahpra_nums = rx_hits["AHPRA_NUMBER"]
    presc_nums = rx_hits["PRESCRIPTION_NUMBER"]
    dates = dates_spacy or rx_hits["DATE_DMY"]

    patient_name = people[0] if people else None
    doctor_name = None
    if "dr." in text.lower() or "dr " in text.lower():
        for p in people:
            if p != patient_name:
                doctor_name = p
                break
        if doctor_name is None and len(people) > 1:
            doctor_name = people[1]
    else:
        doctor_name = people[1] if len(people) > 1 else None

    facility_name = orgs[0] if orgs else None

    return {
        "prescription_number": presc_nums[0] if presc_nums else None,
        "prescription_date": dates[0] if dates else None,
        "expiry_date": dates[1] if len(dates) > 1 else None,
        "patient_name": patient_name,
        "patient_date_of_birth": None,
        "patient_address": None,
        "patient_medicare_number": medicare[0] if medicare else None,
        "patient_phone": phone[0] if phone else None,
        "doctor_name": doctor_name,
        "doctor_provider_number": None,
        "doctor_ahpra_number": ahpra_nums[0] if ahpra_nums else None,
        "doctor_signature_date": None,
        "facility_name": facility_name,
        "facility_address": None,
        "facility_phone": phone[1] if len(phone) > 1 else None,
        "facility_abn": abn[0] if abn else None,
        "medication_name": None,
        "medication_dosage_form": None,
        "medication_strength": None,
        "medication_quantity": None,
        "medication_frequency": None,
        "medication_duration": None,
        "medication_instructions": None,
        "medication_repeats": None,
        "extraction_method": "spacy_en_rules",
    }


def load_ocr_text_by_doc(config: dict) -> pd.DataFrame:
    """Load concatenated OCR text per doc_id from local ``predictions/ocr/*.json``."""
    ocr_dir: Path = config["predictions_dir"] / "ocr"
    if not ocr_dir.exists():
        return pd.DataFrame(columns=["doc_id", "text"])
    rows: list[dict[str, str]] = []
    for path in sorted(ocr_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skip OCR file {}: {}", path, exc)
            continue
        doc_id = str(data.get("doc_id", path.stem))
        parts: list[str] = []
        for page in data.get("pages", []) or []:
            parts.append(str(page.get("text", "")))
        rows.append({"doc_id": doc_id, "text": "\n".join(parts)})
    return pd.DataFrame(rows)


def extract_fields_from_ocr(config: dict) -> pd.DataFrame:
    """
    Build the same flat field schema as label-based extraction, using spaCy + rules on OCR text.
    """
    ocr_df = load_ocr_text_by_doc(config)
    if ocr_df.empty:
        logger.info("No OCR JSON under predictions/ocr; spaCy extraction skipped.")
        return ocr_df

    from use_cases.document_intelligence.ensure_spacy_model import ensure_en_core_web_sm

    if not ensure_en_core_web_sm():
        logger.warning(
            "spaCy pipeline unavailable (install document_intelligence extra or run ensure_spacy_model.py)."
        )
        return pd.DataFrame()

    nlp = get_nlp()
    out_rows = []
    for _, row in ocr_df.iterrows():
        flat = _flatten_spacy_doc(str(row.get("text", "")), nlp)
        flat["doc_id"] = row["doc_id"]
        out_rows.append(flat)

    cols_order = ["doc_id"] + [
        c for c in _flatten_spacy_doc("", nlp) if c != "doc_id" and c != "extraction_method"
    ]
    df = pd.DataFrame(out_rows)
    if "extraction_method" in df.columns:
        cols_order.append("extraction_method")
    df = df.reindex(columns=[c for c in cols_order if c in df.columns])
    logger.info("spaCy/rule extraction produced {} rows", len(df))
    return df
