"""
Inventory optimisation metrics: forecast error (MAE/RMSE/MAPE), write-off reduction, service level.
"""

import numpy as np
import pandas as pd


def forecast_metrics(
    actual: pd.Series,
    predicted: pd.Series,
) -> dict[str, float]:
    """MAE, RMSE, MAPE for demand forecasts."""
    mask = (actual.notna()) & (predicted.notna()) & (actual > 0)
    if not mask.any():
        return {"mae": 0.0, "rmse": 0.0, "mape": 0.0}
    a, p = actual[mask], predicted[mask]
    mae = float(np.abs(a - p).mean())
    rmse = float(np.sqrt(((a - p) ** 2).mean()))
    mape = float((np.abs(a - p) / a).mean() * 100)
    return {"mae": mae, "rmse": rmse, "mape": mape}


def writeoff_risk_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
    y_prob: pd.Series | None = None,
) -> dict[str, float]:
    """Accuracy, F1, precision, recall for write-off risk classification."""
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    y_true = y_true.astype(int)
    y_pred = y_pred.astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
    }


def replenishment_summary(recommendations: pd.DataFrame) -> dict[str, float]:
    """Summary of replenishment recommendations: count below ROP, total reorder qty."""
    if recommendations is None or len(recommendations) == 0:
        return {"below_rop_count": 0, "reorder_lines": 0, "total_reorder_qty": 0.0}
    below = recommendations.get("below_rop", pd.Series(dtype=bool))
    reorder_qty = pd.to_numeric(
        recommendations.get("reorder_qty", 0), errors="coerce"
    ).fillna(0)
    return {
        "below_rop_count": int(below.sum()) if below is not None else 0,
        "reorder_lines": int((reorder_qty > 0).sum()),
        "total_reorder_qty": float(reorder_qty.sum()),
    }
