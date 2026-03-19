"""
Nominal checks: config and imports work for local (non-Databricks) runs.
"""

import pytest


@pytest.fixture(autouse=True)
def _reco_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RECO_DATA_SOURCE", "local")


def test_get_config_local_source() -> None:
    from use_cases.recommendation_engine.config import get_config

    cfg = get_config()
    assert cfg["data_source"] == "local"
    assert cfg["local_data_dir"].name == "local"


def test_default_catalog_schema_helper() -> None:
    from utils.use_case_utils import DEFAULT_CATALOG_SCHEMA

    assert DEFAULT_CATALOG_SCHEMA.startswith("ebos_uc_demo.")
