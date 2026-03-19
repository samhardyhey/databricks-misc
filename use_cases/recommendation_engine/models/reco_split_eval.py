"""
Shared temporal train/val split and MLflow-aligned offline metrics for recommendation models.

All reco trainers should use the same split protocol so MLflow runs are comparable.
Metrics logged (same keys across experiments): val_precision_at_k, val_recall_at_k, val_ndcg_at_k.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from use_cases.recommendation_engine.models.evaluation import evaluate_recommendations

# Keep K identical across item_similarity, ALS, LightFM, ranker for fair comparison.
RECOMMENDATION_OFFLINE_EVAL_K = 10
DEFAULT_VAL_FRACTION = 0.2


def offline_max_eval_users() -> int:
    return int(os.environ.get("RECO_OFFLINE_MAX_EVAL_USERS", "500"))


def ensure_interaction_ts_col(interactions: pd.DataFrame) -> str:
    if "interaction_timestamp" in interactions.columns:
        return "interaction_timestamp"
    if "timestamp" in interactions.columns:
        return "timestamp"
    raise ValueError("interactions must include interaction_timestamp or timestamp")


def temporal_train_val_split(
    interactions: pd.DataFrame,
    val_fraction: float = DEFAULT_VAL_FRACTION,
    ts_col: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Sort events by time and put the last val_fraction of rows in validation.
    Training algorithms must fit on train only; evaluation uses val purchases as relevance.
    """
    col = ts_col or ensure_interaction_ts_col(interactions)
    df = interactions.copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    df = df.dropna(subset=[col]).sort_values(col).reset_index(drop=True)
    n = len(df)
    if n < 10:
        return df, df.iloc[0:0]
    split_idx = max(1, int(n * (1 - float(val_fraction))))
    train = df.iloc[:split_idx].copy()
    val = df.iloc[split_idx:].copy()
    return train, val


def purchases_truth(val_interactions: pd.DataFrame) -> pd.DataFrame:
    """Relevant items: purchases in the validation period."""
    df = val_interactions.copy()
    if "action_type" in df.columns:
        df = df[df["action_type"] == "purchased"]
    out = df[["customer_id", "product_id"]].drop_duplicates()
    return out.assign(
        customer_id=lambda x: x["customer_id"].astype(str),
        product_id=lambda x: x["product_id"].astype(str),
    )


def standard_offline_metrics(eval_dict: dict[str, float]) -> dict[str, float]:
    """Unified MLflow metric names for cross-model comparison."""
    return {
        "val_precision_at_k": float(eval_dict.get("precision_at_k", 0.0)),
        "val_recall_at_k": float(eval_dict.get("recall_at_k", 0.0)),
        "val_ndcg_at_k": float(eval_dict.get("ndcg_at_k", 0.0)),
    }


def evaluate_prediction_df(
    pred_df: pd.DataFrame, truth_df: pd.DataFrame, k: int
) -> dict[str, float]:
    if pred_df is None or truth_df is None or pred_df.empty or truth_df.empty:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "ndcg_at_k": 0.0}
    p = pred_df.assign(
        customer_id=lambda x: x["customer_id"].astype(str),
        product_id=lambda x: x["product_id"].astype(str),
    )
    t = truth_df.assign(
        customer_id=lambda x: x["customer_id"].astype(str),
        product_id=lambda x: x["product_id"].astype(str),
    )
    return evaluate_recommendations(p, t, k=k)


def log_common_reco_eval_params_mlflow(
    val_fraction: float, k: int, n_train_events: int, n_val_events: int
) -> dict[str, Any]:
    """Return dict suitable for mlflow.log_params (caller runs inside active run)."""
    return {
        "reco_eval_protocol": "temporal_split_interactions",
        "reco_val_fraction": val_fraction,
        "reco_eval_k": k,
        "reco_n_train_events": n_train_events,
        "reco_n_val_events": n_val_events,
    }
