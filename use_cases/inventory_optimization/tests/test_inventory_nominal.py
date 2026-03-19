"""
Nominal checks: config resolves for local (non-Databricks) runs.
"""

import pandas as pd
import pytest

from use_cases.inventory_optimization.models.evaluation import (
    forecast_metrics,
    replenishment_summary,
    writeoff_risk_metrics,
)


@pytest.fixture(autouse=True)
def _inventory_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INVENTORY_DATA_SOURCE", "local")


def test_get_config_local_source() -> None:
    from use_cases.inventory_optimization.config import get_config

    cfg = get_config()
    assert cfg["data_source"] == "local"


def test_get_config_uc_fields_null_when_local() -> None:
    from use_cases.inventory_optimization.config import get_config

    cfg = get_config()
    assert cfg["input_bronze_schema"] is None
    assert cfg["input_silver_schema"] is None
    assert cfg["input_gold_schema"] is None
    assert cfg["output_schema"] is None


def test_forecast_metrics_known_values() -> None:
    actual = pd.Series([100.0, 100.0])
    predicted = pd.Series([90.0, 110.0])
    m = forecast_metrics(actual, predicted)
    assert m["mae"] == pytest.approx(10.0)
    assert m["rmse"] == pytest.approx(10.0)
    assert m["mape"] == pytest.approx(10.0)


def test_forecast_metrics_all_nan_or_non_positive_returns_zeros() -> None:
    actual = pd.Series([0.0, 0.0])
    predicted = pd.Series([1.0, 2.0])
    m = forecast_metrics(actual, predicted)
    assert m == {"mae": 0.0, "rmse": 0.0, "mape": 0.0}


def test_writeoff_risk_metrics_perfect_predictions() -> None:
    y_true = pd.Series([0, 1, 0, 1])
    y_pred = pd.Series([0, 1, 0, 1])
    m = writeoff_risk_metrics(y_true, y_pred)
    assert m["accuracy"] == pytest.approx(1.0)
    assert m["f1"] == pytest.approx(1.0)


def test_replenishment_summary_counts_lines_and_quantity() -> None:
    rec = pd.DataFrame(
        {
            "below_rop": [True, False, True],
            "reorder_qty": [10.0, 0.0, 5.5],
        }
    )
    s = replenishment_summary(rec)
    assert s["below_rop_count"] == 2
    assert s["reorder_lines"] == 2
    assert s["total_reorder_qty"] == pytest.approx(15.5)


def test_replenishment_summary_empty_dataframe() -> None:
    assert replenishment_summary(pd.DataFrame()) == {
        "below_rop_count": 0,
        "reorder_lines": 0,
        "total_reorder_qty": 0.0,
    }
