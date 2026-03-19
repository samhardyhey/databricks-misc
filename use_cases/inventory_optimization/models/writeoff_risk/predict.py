"""
Batch apply the inventory write-off risk classifier to current inventory.

Intended for:
- Local runs via `python use_cases/inventory_optimization/models/writeoff_risk/predict.py`
- Databricks jobs for batch scoring (gold_writeoff_risk_scores, etc.).

Behaviour:
- Uses inventory_optimization.config.get_config() for local vs catalog and schema.
- Loads inventory data via load_inventory_data.
- Builds features with build_writeoff_risk_features.
- Loads a model from MLflow (model URI configurable via env).
- Writes scores to:
  - pandas DataFrame (local) or
  - Unity Catalog table when running on Databricks (Spark available).
"""

import os
from typing import Optional

import pandas as pd
from loguru import logger

from use_cases.inventory_optimization.config import get_config
from use_cases.inventory_optimization.models.data_loading import load_inventory_data
from use_cases.inventory_optimization.models.writeoff_risk.core import (
    build_writeoff_risk_features,
    predict_writeoff_risk,
    writeoff_inference_feature_columns,
)
from utils.env_utils import is_running_on_databricks


def _load_model(model_uri: Optional[str] = None):
    """
    Try to load write-off risk model from MLflow. Returns the model or None if:
    - mlflow is not installed, or
    - WRITEOFF_RISK_MODEL_URI is not set.

    This keeps `make inventory-writeoff-apply` from failing on local setups where
    no registry model has been configured yet, while still allowing Databricks
    jobs to supply a concrete URI.
    """
    uri = (
        model_uri
        or os.environ.get("WRITEOFF_RISK_MODEL_URI")
        or "models:/inventory_optimization-writeoff_risk@Champion"
    )
    if not uri:
        logger.info(
            "Write-off risk predict skipped: WRITEOFF_RISK_MODEL_URI is not set; "
            "set it to an MLflow model URI to enable local batch scoring."
        )
        return None
    logger.info("Loading write-off risk model from {}", uri)
    import mlflow
    import mlflow.sklearn  # noqa: F401

    return mlflow.sklearn.load_model(uri)


def main(model_uri: Optional[str] = None) -> pd.DataFrame:
    cfg = get_config()
    spark = None
    if cfg["data_source"] == "catalog" and is_running_on_databricks():
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("WriteoffRiskPredict").getOrCreate()

    data = load_inventory_data(config=cfg, spark=spark)
    inventory = data.get("inventory")
    orders = data.get("orders")
    products = data.get("products")
    if inventory is None or len(inventory) == 0:
        logger.warning("No inventory data; nothing to score.")
        if spark is not None:
            spark.stop()
        return pd.DataFrame()

    features_df = build_writeoff_risk_features(
        inventory, orders=orders, products=products
    )
    # Ensure an index suitable for joining back
    if "inventory_id" in features_df.columns:
        features_df = features_df.set_index("inventory_id")

    model = _load_model(model_uri=model_uri)
    if model is None:
        logger.info(
            "Write-off risk predict: no model available; returning empty DataFrame."
        )
        if spark is not None:
            spark.stop()
        return pd.DataFrame()
    feature_cols = writeoff_inference_feature_columns(features_df)
    scores = predict_writeoff_risk(model, features_df, feature_cols)
    out = features_df.copy()
    out["writeoff_risk_score"] = scores

    if spark is not None:
        from pyspark.sql import functions as F

        schema = cfg["output_schema"]
        table = os.environ.get(
            "WRITEOFF_RISK_SCORES_TABLE",
            f"{schema}.gold_writeoff_risk_scores",
        )
        logger.info("Writing write-off risk scores to {}", table)
        sdf = spark.createDataFrame(out.reset_index())
        sdf = sdf.withColumn("scored_at", F.current_timestamp())
        sdf.write.mode("overwrite").saveAsTable(table)

    if spark is not None:
        spark.stop()

    return out


if __name__ == "__main__":
    df = main()
    logger.info("Scored {} inventory rows for write-off risk", len(df))
