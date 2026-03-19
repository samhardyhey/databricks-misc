"""
Nominal checks: doc-intel config defaults and paths.
"""

import pytest


@pytest.fixture(autouse=True)
def _docint_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCINT_DATA_SOURCE", "local")


def test_get_data_source_local() -> None:
    from use_cases.document_intelligence.config import get_data_source

    assert get_data_source() == "local"


def test_volume_default_uses_demo_catalog() -> None:
    from use_cases.document_intelligence.config import get_documents_volume_path

    assert "/ebos_uc_demo/" in get_documents_volume_path()
