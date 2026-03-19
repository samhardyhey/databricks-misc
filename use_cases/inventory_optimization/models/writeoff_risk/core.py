"""
Core write-off risk classifier utilities.

Moved here from use_cases/inventory_optimization/writeoff_risk_classifier.py so that
all writeoff-risk-specific code lives under models/writeoff_risk/.
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger


def build_writeoff_risk_features(
    inventory: pd.DataFrame,
    orders: Optional[pd.DataFrame] = None,
    products: Optional[pd.DataFrame] = None,
    horizon_days: int = 30,
) -> pd.DataFrame:
    """
    Build feature set for write-off risk: days_until_expiry, stock level, demand proxy, turnover.
    Uses pharmacy_id as warehouse_id when present.
    """
    inv = inventory.copy()
    if "warehouse_id" not in inv.columns and "pharmacy_id" in inv.columns:
        inv["warehouse_id"] = inv["pharmacy_id"].astype(str)

    # Days until expiry (from expiry_date or precomputed)
    if "days_until_expiry" in inv.columns:
        inv["days_until_expiry"] = pd.to_numeric(
            inv["days_until_expiry"], errors="coerce"
        )
    elif "expiry_date" in inv.columns:
        inv["expiry_date"] = pd.to_datetime(inv["expiry_date"], errors="coerce")
        inv["days_until_expiry"] = (
            inv["expiry_date"] - pd.Timestamp.now().normalize()
        ).dt.days
    else:
        inv["days_until_expiry"] = np.nan

    inv["current_stock"] = pd.to_numeric(
        inv.get("current_stock", 0), errors="coerce"
    ).fillna(0)
    inv["max_stock"] = pd.to_numeric(inv.get("max_stock", 1), errors="coerce").replace(
        0, 1
    )
    inv["stock_pct"] = (inv["current_stock"] / inv["max_stock"]).clip(0, 1)

    # Demand proxy: orders in last 90 days per product x warehouse
    if orders is not None and len(orders) and "product_id" in orders.columns:
        orders = orders.copy()
        orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
        cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=90)
        recent = orders[orders["order_date"] >= cutoff]
        wh_col = "pharmacy_id" if "pharmacy_id" in recent.columns else "warehouse_id"
        if wh_col not in recent.columns and "customer_id" in recent.columns:
            recent = recent.rename(columns={"customer_id": "warehouse_id"})
            wh_col = "warehouse_id"
        qty_col = "quantity" if "quantity" in recent.columns else "total_amount"
        if wh_col in recent.columns and "product_id" in recent.columns:
            demand_90 = (
                recent.groupby(["product_id", wh_col])[qty_col]
                .sum()
                .reset_index()
                .rename(columns={qty_col: "demand_90d", wh_col: "warehouse_id"})
            )
            demand_90["forecast_demand_30d"] = (demand_90["demand_90d"] / 3).clip(
                0, 1e6
            )
            inv = inv.merge(
                demand_90[["product_id", "warehouse_id", "forecast_demand_30d"]],
                on=["product_id", "warehouse_id"],
                how="left",
            )
    if "forecast_demand_30d" not in inv.columns:
        inv["forecast_demand_30d"] = 0
    else:
        inv["forecast_demand_30d"] = inv["forecast_demand_30d"].fillna(0)

    # Turnover proxy: demand_90d / (current_stock + 1)
    inv["turnover_rate"] = inv["forecast_demand_30d"] * 3 / (inv["current_stock"] + 1)

    # Seasonality: month
    inv["month"] = pd.Timestamp.now().month

    # Product category if available
    if products is not None and "product_id" in products.columns:
        cat_col = (
            "therapeutic_category"
            if "therapeutic_category" in products.columns
            else "category"
        )
        if cat_col not in products.columns:
            cat_col = [
                c for c in products.columns if "cat" in c.lower() or "type" in c.lower()
            ]
            cat_col = cat_col[0] if cat_col else None
        if cat_col:
            inv = inv.merge(
                products[["product_id", cat_col]].drop_duplicates("product_id"),
                on="product_id",
                how="left",
            )
            inv[cat_col] = inv[cat_col].astype(str).fillna("unknown")

    return inv


# When the label is a direct function of days_until_expiry, that column must not be in X.
_EXCLUDE_FROM_FEATURES = {
    "will_expire_30d": {"days_until_expiry"},
}


def default_writeoff_feature_columns(df: pd.DataFrame) -> list[str]:
    """Non-leaky numeric/categorical columns for ``will_expire_30d`` (demo / inventory snapshot)."""
    base = [
        "current_stock",
        "stock_pct",
        "forecast_demand_30d",
        "turnover_rate",
        "month",
    ]
    out = [c for c in base if c in df.columns]
    for c in ("therapeutic_category", "category"):
        if c in df.columns and c not in out:
            out.append(c)
    return out


def writeoff_inference_feature_columns(
    df: pd.DataFrame, target_col: str = "will_expire_30d"
) -> list[str]:
    """Match train-time feature selection for batch scoring (excludes leaky columns for target)."""
    banned = _EXCLUDE_FROM_FEATURES.get(target_col, set())
    return [c for c in default_writeoff_feature_columns(df) if c not in banned]


def train_writeoff_risk_classifier(
    features_df: pd.DataFrame,
    target_col: str = "will_expire_30d",
    feature_cols: Optional[list[str]] = None,
    test_size: float = 0.2,
    random_state: int = 42,
):
    """
    Train binary classifier for ``will_expire_30d`` (label built from ``days_until_expiry`` elsewhere).

    **Feature hygiene:** ``days_until_expiry`` is excluded from training features when the target is
    ``will_expire_30d``, since the label is defined from the same quantity (avoids trivial leakage).
    For production, prefer labels derived from historical write-off events at an explicit as-of date.
    """
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        f1_score,
        precision_score,
        recall_score,
    )
    from sklearn.model_selection import train_test_split

    try:
        import lightgbm as lgb

        model_cls = lgb.LGBMClassifier
        model_kw = {"n_estimators": 50, "random_state": random_state, "verbosity": -1}
    except ImportError:
        from sklearn.ensemble import RandomForestClassifier

        model_cls = RandomForestClassifier
        model_kw = {"n_estimators": 50, "random_state": random_state}

    df = features_df.copy()
    if target_col not in df.columns:
        raise ValueError(f"Target column {target_col} not in DataFrame")

    banned = _EXCLUDE_FROM_FEATURES.get(target_col, set())
    if feature_cols is None:
        feature_cols = default_writeoff_feature_columns(df)
    feature_cols = [c for c in feature_cols if c not in banned]

    if not feature_cols:
        raise ValueError(
            "No feature columns left after excluding leaky columns; check input schema."
        )

    df = df.dropna(subset=feature_cols + [target_col])
    if len(df) < 20:
        logger.warning("Very few rows after dropna; consider relaxing features")

    X = df[feature_cols].copy()
    for c in X.columns:
        if X[c].dtype not in (object,) and str(X[c].dtype) != "category":
            X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0.0)

    y = df[target_col].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y if y.nunique() > 1 else None,
    )

    obj_cols = [
        c
        for c in feature_cols
        if X_train[c].dtype == object or str(X_train[c].dtype) == "category"
    ]
    num_cols = [c for c in feature_cols if c not in obj_cols]

    if obj_cols:
        from sklearn.compose import ColumnTransformer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OrdinalEncoder

        parts = [
            (
                "cat",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                obj_cols,
            ),
        ]
        if num_cols:
            parts.append(("num", "passthrough", num_cols))
        preprocess = ColumnTransformer(transformers=parts)
        model: object = Pipeline([("prep", preprocess), ("clf", model_cls(**model_kw))])
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        proba = (
            model.predict_proba(X_test)[:, 1]
            if hasattr(model, "predict_proba")
            else None
        )
    else:
        estimator = model_cls(**model_kw)
        model = estimator
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        proba = (
            model.predict_proba(X_test)[:, 1]
            if hasattr(model, "predict_proba")
            else None
        )

    metrics = {
        "accuracy": float(accuracy_score(y_test, pred)),
        "f1": float(f1_score(y_test, pred, zero_division=0)),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "positive_rate_holdout": float(y_test.mean()),
    }
    if proba is not None:
        metrics["pr_auc"] = float(average_precision_score(y_test, proba))
    logger.info("Write-off risk classifier metrics: {}", metrics)
    return model, list(feature_cols), metrics


def predict_writeoff_risk(
    model,
    features_df: pd.DataFrame,
    feature_cols: list[str],
) -> pd.Series:
    """Predict probability or class for write-off risk."""
    X = features_df[feature_cols].copy()
    for c in X.columns:
        if X[c].dtype == object or str(X[c].dtype) == "category":
            X[c] = X[c].astype(str).replace({"nan": "", "None": ""})
        else:
            X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0.0)
    if hasattr(model, "predict_proba"):
        return pd.Series(model.predict_proba(X)[:, 1], index=features_df.index)
    return pd.Series(model.predict(X), index=features_df.index)
