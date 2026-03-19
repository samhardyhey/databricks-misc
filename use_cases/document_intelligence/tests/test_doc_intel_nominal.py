"""
Nominal checks: doc-intel config defaults and paths.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from use_cases.document_intelligence import predictions_io


@pytest.fixture(autouse=True)
def _docint_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCINT_DATA_SOURCE", "local")


def test_get_data_source_local() -> None:
    from use_cases.document_intelligence.config import get_data_source

    assert get_data_source() == "local"


def test_volume_default_uses_demo_catalog() -> None:
    from use_cases.document_intelligence.config import get_documents_volume_path

    assert "/ebos_uc_demo/" in get_documents_volume_path()


def test_get_config_local_paths_are_under_base_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from use_cases.document_intelligence.config import get_config

    p = tmp_path / "docintel_run"
    p.mkdir()
    monkeypatch.setenv("DOCINT_DATA_SOURCE", "local")
    monkeypatch.setenv("DOCINT_BASE_DIR", str(p))
    cfg = get_config()
    assert cfg["data_source"] == "local"
    assert cfg["base_dir"] == p.resolve()
    assert cfg["documents_dir"] == p / "documents"
    assert cfg["predictions_dir"] == p / "predictions"
    assert "ebos_uc_demo" in cfg["catalog_schema"]


def test_row_to_nested_flattens_into_expected_annotator_schema() -> None:
    row = pd.Series(
        {
            "doc_id": "rx1",
            "prescription_number": "PN99",
            "patient_name": "Jane Doe",
            "doctor_name": "Dr Who",
            "medication_name": "Aspirin",
            "unknown_column": "ignored",
        }
    )
    nested = predictions_io._row_to_nested(row)
    assert nested["prescription_number"] == "PN99"
    assert nested["patient"]["name"] == "Jane Doe"
    assert nested["doctor"]["name"] == "Dr Who"
    assert nested["medication"]["name"] == "Aspirin"
    assert "unknown_column" not in nested


def test_write_ocr_output_local_writes_grouped_pages_json(tmp_path: Path) -> None:
    ocr_df = pd.DataFrame(
        [
            {"doc_id": "a", "page": 2, "text": "second"},
            {"doc_id": "a", "page": 1, "text": "first"},
        ]
    )
    cfg = {"data_source": "local", "predictions_dir": tmp_path / "pred"}
    predictions_io.write_ocr_output(cfg, ocr_df)
    out_file = cfg["predictions_dir"] / "ocr" / "a.json"
    assert out_file.is_file()
    payload = json.loads(out_file.read_text())
    assert payload["doc_id"] == "a"
    assert [p["page"] for p in payload["pages"]] == [1, 2]
    assert payload["pages"][0]["text"] == "first"
