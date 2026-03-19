"""
Nominal checks: config and imports work for local (non-Databricks) runs.
"""

import pandas as pd
import pytest

from use_cases.recommendation_engine.models.evaluation import evaluate_recommendations
from use_cases.recommendation_engine.models.reco_split_eval import (
    ensure_interaction_ts_col,
    log_common_reco_eval_params_mlflow,
    standard_offline_metrics,
    temporal_train_val_split,
)


@pytest.fixture(autouse=True)
def _reco_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RECO_DATA_SOURCE", "local")


def test_get_config_local_source() -> None:
    from use_cases.recommendation_engine.config import get_config

    cfg = get_config()
    assert cfg["data_source"] == "local"
    assert cfg["local_data_dir"].name == "local"


def test_get_config_includes_mlflow_keys_when_local() -> None:
    from use_cases.recommendation_engine.config import get_config

    cfg = get_config()
    assert "mlflow_tracking_uri" in cfg
    assert "mlflow_registry_uri" in cfg
    assert cfg["input_silver_schema"] is None
    assert cfg["output_schema"] is None


def test_default_catalog_schema_helper() -> None:
    from utils.use_case_utils import DEFAULT_CATALOG_SCHEMA

    assert DEFAULT_CATALOG_SCHEMA.startswith("ebos_uc_demo.")


def test_temporal_train_val_split_last_fraction_goes_to_validation() -> None:
    ts = pd.date_range("2024-01-01", periods=20, freq="h")
    interactions = pd.DataFrame(
        {
            "customer_id": range(20),
            "product_id": range(20),
            "interaction_timestamp": ts,
        }
    )
    train, val = temporal_train_val_split(interactions, val_fraction=0.2)
    assert len(train) == 16
    assert len(val) == 4
    assert val["interaction_timestamp"].min() >= train["interaction_timestamp"].max()


def test_ensure_interaction_ts_col_prefers_canonical_name() -> None:
    df = pd.DataFrame(
        {
            "interaction_timestamp": [1],
            "timestamp": [2],
            "customer_id": ["a"],
        }
    )
    assert ensure_interaction_ts_col(df) == "interaction_timestamp"


def test_standard_offline_metrics_normalizes_mlflow_keys() -> None:
    raw = {"precision_at_k": 0.1, "recall_at_k": 0.2, "ndcg_at_k": 0.3}
    out = standard_offline_metrics(raw)
    assert out == {
        "val_precision_at_k": 0.1,
        "val_recall_at_k": 0.2,
        "val_ndcg_at_k": 0.3,
    }
    sparse = standard_offline_metrics({})
    assert sparse["val_precision_at_k"] == 0.0


def test_log_common_reco_eval_params_mlflow_structure() -> None:
    p = log_common_reco_eval_params_mlflow(0.2, 10, 100, 25)
    assert p["reco_eval_protocol"] == "temporal_split_interactions"
    assert p["reco_val_fraction"] == 0.2
    assert p["reco_eval_k"] == 10
    assert p["reco_n_train_events"] == 100
    assert p["reco_n_val_events"] == 25


def test_evaluate_recommendations_hits_known_user_item_pair() -> None:
    pred = pd.DataFrame(
        {
            "customer_id": ["u1", "u1", "u1"],
            "product_id": ["i_miss", "i_hit", "i_other"],
        }
    )
    truth = pd.DataFrame({"customer_id": ["u1"], "product_id": ["i_hit"]})
    m = evaluate_recommendations(pred, truth, k=3)
    assert m["precision_at_k"] == pytest.approx(1 / 3)
    assert m["recall_at_k"] == 1.0
    assert m["ndcg_at_k"] > 0.0
