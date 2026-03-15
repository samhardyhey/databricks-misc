"""
Local entrypoint: load CSV data, train write-off risk classifier, run replenishment optimizer, evaluate.
Run from repo root: make inventory-run  or  python use_cases/inventory_optimization/run_inventory_local.py
Expects data/local/ with inventory.csv, expiry_batches.csv, writeoff_events.csv, orders.csv, products.csv
(e.g. after make data-local-generate-quick).
"""

import os
from pathlib import Path

import pandas as pd
from loguru import logger

from use_cases.inventory_optimization.data_loading import (
    DEFAULT_LOCAL_DATA_DIR,
    load_inventory_data_local,
)
from use_cases.inventory_optimization.writeoff_risk_classifier import (
    build_writeoff_risk_features,
    predict_writeoff_risk,
    train_writeoff_risk_classifier,
)
from use_cases.inventory_optimization.replenishment_optimizer import (
    compute_replenishment_recommendations,
)
from use_cases.inventory_optimization.evaluation import replenishment_summary


def create_sample_inventory_data() -> dict[str, pd.DataFrame]:
    """Minimal synthetic data when local CSVs are missing."""
    import numpy as np

    n = 150
    np.random.seed(42)
    products = list(range(1, 11))
    warehouses = [f"WH_{i}" for i in range(1, 6)]
    inventory = pd.DataFrame({
        "inventory_id": [f"INV_{i}" for i in range(n)],
        "pharmacy_id": np.random.choice(warehouses, n),
        "product_id": np.random.choice(products, n),
        "current_stock": np.random.randint(0, 200, n),
        "max_stock": np.random.randint(100, 500, n),
        "expiry_date": pd.date_range("2025-01-01", periods=n, freq="D") + pd.Timedelta(days=np.random.randint(30, 400, n)),
    })
    inventory["warehouse_id"] = inventory["pharmacy_id"]
    orders = pd.DataFrame({
        "order_id": range(300),
        "pharmacy_id": np.random.choice(warehouses, 300),
        "product_id": np.random.choice(products, 300),
        "order_date": pd.date_range("2024-06-01", periods=300, freq="D"),
        "quantity": np.random.randint(1, 30, 300),
    })
    orders["warehouse_id"] = orders["pharmacy_id"]
    writeoff_events = pd.DataFrame({
        "event_id": [f"WO_{i}" for i in range(20)],
        "product_id": np.random.choice(products, 20),
        "warehouse_id": np.random.choice(warehouses, 20),
        "quantity": np.random.randint(1, 10, 20),
        "reason": np.random.choice(["expired", "damaged", "obsolete"], 20),
        "timestamp": pd.date_range("2024-01-01", periods=20, freq="D"),
    })
    products_df = pd.DataFrame({
        "product_id": products,
        "product_name": [f"Product_{p}" for p in products],
    })
    return {
        "inventory": inventory,
        "orders": orders,
        "writeoff_events": writeoff_events,
        "products": products_df,
        "expiry_batches": None,
    }


def main(data_dir: Path | None = None) -> dict:
    data_dir = data_dir or Path(os.environ.get("LOCAL_DATA_PATH", str(DEFAULT_LOCAL_DATA_DIR)))
    logger.info("Loading inventory data from {}", data_dir)
    data = load_inventory_data_local(data_dir)

    # Fallback to sample data if key tables missing
    if data.get("inventory") is None or data.get("orders") is None:
        logger.warning("Missing inventory.csv or orders.csv; using sample data")
        data = create_sample_inventory_data()

    inventory = data["inventory"]
    orders = data["orders"]
    products = data.get("products")

    # --- Write-off risk features and label ---
    # Label: will expire in next 30 days (from days_until_expiry)
    features_df = build_writeoff_risk_features(inventory, orders=orders, products=products)
    if "days_until_expiry" in features_df.columns:
        features_df["will_expire_30d"] = (features_df["days_until_expiry"] >= 0) & (
            features_df["days_until_expiry"] <= 30
        )
    else:
        features_df["will_expire_30d"] = False
    features_df["will_expire_30d"] = features_df["will_expire_30d"].astype(int)

    # Train classifier (skip if too few positive samples)
    writeoff_metrics = {}
    if features_df["will_expire_30d"].sum() >= 5 and features_df["will_expire_30d"].sum() < len(features_df) - 5:
        model, feature_cols, writeoff_metrics = train_writeoff_risk_classifier(features_df)
        features_df["writeoff_risk_score"] = predict_writeoff_risk(model, features_df, feature_cols)
        logger.info("Write-off risk classifier trained; metrics: {}", writeoff_metrics)
    else:
        logger.info("Skipping write-off classifier (insufficient label variance); using placeholder score")
        features_df["writeoff_risk_score"] = 0.0

    # --- Replenishment ---
    replen = compute_replenishment_recommendations(
        inventory,
        orders,
        lead_time_days=7.0,
        service_level=0.95,
    )
    replen_summary = replenishment_summary(replen)
    logger.info("Replenishment summary: {}", replen_summary)

    return {
        "writeoff_risk_metrics": writeoff_metrics,
        "replenishment_summary": replen_summary,
        "recommendations": replen,
    }


if __name__ == "__main__":
    import sys

    data_dir = Path(os.environ.get("LOCAL_DATA_PATH", str(DEFAULT_LOCAL_DATA_DIR)))
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    result = main(data_dir)
    logger.info("inventory local run done: {}", {k: v for k, v in result.items() if k != "recommendations"})
