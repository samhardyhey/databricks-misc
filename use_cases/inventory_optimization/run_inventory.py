"""
Single entrypoint for inventory optimisation: runs locally or on Databricks.
Data source is switched via config (config.get_config()): local CSV vs Unity Catalog.
- Local: INVENTORY_DATA_SOURCE=local (default when not on Databricks); data from LOCAL_DATA_PATH / data/local.
- Databricks: INVENTORY_DATA_SOURCE=auto (default) -> catalog when DATABRICKS_RUNTIME_VERSION is set; Spark loads from catalog.
Override with INVENTORY_DATA_SOURCE=local|catalog|auto and INVENTORY_CATALOG_SCHEMA, LOCAL_DATA_PATH as needed.
Run: make inventory-run (local)  or  deploy as Databricks job with this script.
"""

import pandas as pd
from loguru import logger

from use_cases.inventory_optimization.config import get_config
from use_cases.inventory_optimization.models.data_loading import load_inventory_data
from use_cases.inventory_optimization.models.evaluation import replenishment_summary
from use_cases.inventory_optimization.models.replenishment.core import (
    compute_replenishment_recommendations,
)
from use_cases.inventory_optimization.writeoff_risk_classifier import (
    build_writeoff_risk_features,
    predict_writeoff_risk,
    train_writeoff_risk_classifier,
)


def create_sample_inventory_data() -> dict[str, pd.DataFrame]:
    """Minimal synthetic data when local CSVs are missing."""
    import numpy as np

    n = 150
    np.random.seed(42)
    products = list(range(1, 11))
    warehouses = [f"WH_{i}" for i in range(1, 6)]
    inventory = pd.DataFrame(
        {
            "inventory_id": [f"INV_{i}" for i in range(n)],
            "pharmacy_id": np.random.choice(warehouses, n),
            "product_id": np.random.choice(products, n),
            "current_stock": np.random.randint(0, 200, n),
            "max_stock": np.random.randint(100, 500, n),
            "expiry_date": pd.date_range("2025-01-01", periods=n, freq="D")
            + pd.Timedelta(days=np.random.randint(30, 400, n)),
        }
    )
    inventory["warehouse_id"] = inventory["pharmacy_id"]
    orders = pd.DataFrame(
        {
            "order_id": range(300),
            "pharmacy_id": np.random.choice(warehouses, 300),
            "product_id": np.random.choice(products, 300),
            "order_date": pd.date_range("2024-06-01", periods=300, freq="D"),
            "quantity": np.random.randint(1, 30, 300),
        }
    )
    orders["warehouse_id"] = orders["pharmacy_id"]
    writeoff_events = pd.DataFrame(
        {
            "event_id": [f"WO_{i}" for i in range(20)],
            "product_id": np.random.choice(products, 20),
            "warehouse_id": np.random.choice(warehouses, 20),
            "quantity": np.random.randint(1, 10, 20),
            "reason": np.random.choice(["expired", "damaged", "obsolete"], 20),
            "timestamp": pd.date_range("2024-01-01", periods=20, freq="D"),
        }
    )
    products_df = pd.DataFrame(
        {
            "product_id": products,
            "product_name": [f"Product_{p}" for p in products],
        }
    )
    return {
        "inventory": inventory,
        "orders": orders,
        "writeoff_events": writeoff_events,
        "products": products_df,
        "expiry_batches": None,
    }


def main(config: dict | None = None, spark=None) -> dict:
    """
    Load data (from config: local or catalog), train write-off risk, run replenishment, evaluate.
    config: from get_config() if None. spark: required when config["data_source"] == "catalog".
    """
    cfg = config or get_config()
    logger.info(
        "Inventory run: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )
    if cfg["data_source"] == "catalog" and spark is None and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("InventoryRun").getOrCreate()
    elif cfg["data_source"] == "catalog" and spark is None:
        raise RuntimeError(
            "INVENTORY_DATA_SOURCE=catalog requires a SparkSession (e.g. on Databricks)."
        )

    data = load_inventory_data(config=cfg, spark=spark)

    # Fallback to sample data when local and key tables missing
    if cfg["data_source"] == "local" and (
        data.get("inventory") is None or data.get("orders") is None
    ):
        logger.warning("Missing inventory.csv or orders.csv; using sample data")
        data = create_sample_inventory_data()

    inventory = data["inventory"]
    orders = data["orders"]
    products = data.get("products")
    if inventory is None or len(inventory) == 0:
        raise FileNotFoundError(
            "Need inventory data. Local: make inventory-data and set LOCAL_DATA_PATH. "
            "Catalog: ensure medallion has run (silver_inventory, silver_orders)."
        )
    if orders is None or len(orders) == 0:
        raise FileNotFoundError(
            "Need orders data. Local: make inventory-data. Catalog: ensure silver_orders exists."
        )

    # --- Write-off risk features and label ---
    features_df = build_writeoff_risk_features(
        inventory, orders=orders, products=products
    )
    if "days_until_expiry" in features_df.columns:
        features_df["will_expire_30d"] = (
            (features_df["days_until_expiry"] >= 0)
            & (features_df["days_until_expiry"] <= 30)
        ).astype(int)
    else:
        features_df["will_expire_30d"] = 0

    writeoff_metrics = {}
    if (
        features_df["will_expire_30d"].sum() >= 5
        and features_df["will_expire_30d"].sum() < len(features_df) - 5
    ):
        model, feature_cols, writeoff_metrics = train_writeoff_risk_classifier(
            features_df
        )
        features_df["writeoff_risk_score"] = predict_writeoff_risk(
            model, features_df, feature_cols
        )
        logger.info("Write-off risk classifier trained; metrics: {}", writeoff_metrics)
    else:
        logger.info(
            "Skipping write-off classifier (insufficient label variance); using placeholder score"
        )
        features_df["writeoff_risk_score"] = 0.0

    # --- Replenishment ---
    replen = compute_replenishment_recommendations(
        inventory,
        orders,
        lead_time_days=7.0,
        service_level=0.95,
    )
    replen_summary_dict = replenishment_summary(replen)
    logger.info("Replenishment summary: {}", replen_summary_dict)

    return {
        "writeoff_risk_metrics": writeoff_metrics,
        "replenishment_summary": replen_summary_dict,
        "recommendations": replen,
    }


if __name__ == "__main__":
    result = main()
    logger.info(
        "inventory run done: {}",
        {k: v for k, v in result.items() if k != "recommendations"},
    )
