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
import mlflow.prophet  # type: ignore[import-untyped]
import mlflow.sklearn  # type: ignore[import-untyped]
import mlflow.xgboost  # type: ignore[import-untyped]
import numpy as np

from use_cases.inventory_optimization.config import (
    apply_mlflow_config,
    ensure_experiment_artifact_root,
)
import pandas as pd
from loguru import logger


def compare_forecasting_models(
    orders: pd.DataFrame,
    target_column: str,
    time_column: str,
    group_by: Optional[str] = None,
    experiment_name: str = "inventory_demand_forecast",
) -> Dict[str, Any]:
    """
    Minimal placeholder implementation to keep inventory demos working.

    In the full implementation this would:
    - prepare time series features
    - train multiple models (ETS, Prophet, XGBoost)
    - log metrics and artifacts to MLflow
    - return a rich results dictionary.
    """
    if orders is None or len(orders) == 0:
        logger.warning("No orders provided to compare_forecasting_models")
        return {"comparison_summary": {}, "best_model": None}

    y = pd.to_numeric(orders[target_column], errors="coerce").fillna(0.0)
    baseline = float(y.mean())
    mae = float(np.abs(y - baseline).mean())
    rmse = float(np.sqrt(((y - baseline) ** 2).mean()))
    mape = float((np.abs(y - baseline) / np.where(y == 0, 1.0, y)).mean() * 100)

    try:
        apply_mlflow_config()
        ensure_experiment_artifact_root(experiment_name)
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=f"{experiment_name}_naive_mean"):
            mlflow.log_param("model_type", "naive_mean")
            mlflow.log_metrics({"mae": mae, "rmse": rmse, "mape": mape})
    except Exception:
        logger.debug(
            "MLflow logging skipped for compare_forecasting_models", exc_info=True
        )

    logger.info(
        "Baseline demand forecasting metrics: mae={:.3f}, rmse={:.3f}, mape={:.2f}%",
        mae,
        rmse,
        mape,
    )

    return {
        "comparison_summary": {
            "naive_mean": {"mae": mae, "rmse": rmse, "mape": mape},
        },
        "best_model": "naive_mean",
    }
