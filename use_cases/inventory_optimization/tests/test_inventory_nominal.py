"""
Nominal checks: config resolves for local (non-Databricks) runs.
"""

import pytest


@pytest.fixture(autouse=True)
def _inventory_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INVENTORY_DATA_SOURCE", "local")


def test_get_config_local_source() -> None:
    from use_cases.inventory_optimization.config import get_config

    cfg = get_config()
    assert cfg["data_source"] == "local"
