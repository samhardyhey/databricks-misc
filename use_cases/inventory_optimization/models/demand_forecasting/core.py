"""
Core demand forecasting utilities for inventory optimisation.

Copied from use_cases/inventory_optimization/demand_forecasting.py so that
all model-specific code lives under models/demand_forecasting/.

Note: this module is large; only the most important public functions should
normally be imported elsewhere (prepare_forecasting_data, run_xgboost_experiment,
compare_forecasting_models, etc.).
"""

from typing import Any, Dict, Optional

import mlflow
import numpy as np
import pandas as pd
from loguru import logger

from use_cases.inventory_optimization.config import (
    apply_mlflow_config,
    ensure_experiment_artifact_root,
)
from use_cases.inventory_optimization.models.evaluation import forecast_metrics


def compare_forecasting_models(
    orders: pd.DataFrame,
    target_column: str,
    time_column: str,
    group_by: Optional[str] = None,
    experiment_name: str = "inventory_optimization-demand_forecast",
    val_fraction: float = 0.2,
) -> Dict[str, Any]:
    """
    Minimal placeholder: global-mean baseline with temporal train/test split on orders.

    Rows are sorted by ``time_column``; the first (1 - val_fraction) fraction fits the
    mean; metrics are on the held-out tail. Full models (ETS, Prophet, XGBoost) would
    replace this while keeping the same split contract.
    """
    if orders is None or len(orders) == 0:
        logger.warning("No orders provided to compare_forecasting_models")
        return {"comparison_summary": {}, "best_model": None}

    df = orders.copy()
    df[time_column] = pd.to_datetime(df[time_column], errors="coerce")
    df = df.dropna(subset=[time_column]).sort_values(time_column).reset_index(drop=True)
    y_all = pd.to_numeric(df[target_column], errors="coerce").fillna(0.0)
    n = len(df)
    split_i = max(1, int(n * (1.0 - float(val_fraction))))
    if split_i >= n:
        split_i = n - 1
    y_train = y_all.iloc[:split_i]
    y_test = y_all.iloc[split_i:]
    baseline = float(y_train.mean())
    pred_test = pd.Series(np.full(len(y_test), baseline), index=y_test.index)
    metrics = forecast_metrics(y_test, pred_test)

    try:
        apply_mlflow_config()
        ensure_experiment_artifact_root(experiment_name)
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=f"{experiment_name}_naive_mean"):
            mlflow.log_param("model_type", "naive_mean")
            mlflow.log_param("eval_protocol", "temporal_split_orders")
            mlflow.log_param("val_fraction", val_fraction)
            mlflow.log_param("n_train_rows", split_i)
            mlflow.log_param("n_test_rows", int(n - split_i))
            mlflow.log_metrics(metrics)
    except Exception:
        logger.debug(
            "MLflow logging skipped for compare_forecasting_models", exc_info=True
        )

    logger.info(
        "Baseline demand (held-out): mae={:.3f}, rmse={:.3f}, mape={:.2f}%",
        metrics["mae"],
        metrics["rmse"],
        metrics["mape"],
    )

    return {
        "comparison_summary": {
            "naive_mean": metrics,
        },
        "best_model": "naive_mean",
    }
