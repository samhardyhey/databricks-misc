"""
Batch apply the item-to-item similarity model to products.

Intended for:
- Local runs via `python use_cases/recommendation_engine/models/item_similarity/predict.py`
- Databricks jobs for offline candidate generation (future gold_reco_candidates, etc.).

Requires [reco] extra. Run: make reco-install.
"""

import os
from typing import Optional

import mlflow
import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import apply_mlflow_config, get_config
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from utils.env_utils import is_running_on_databricks


def _load_item_similarity_model(model_uri: Optional[str] = None):
    """
    Load item_similarity model from MLflow. Locally set ITEM_SIMILARITY_MODEL_URI to
    a runs:/ or file:// URI; on Databricks jobs can use a registry URI. Returns None if not set.
    """
    uri = model_uri or os.environ.get("ITEM_SIMILARITY_MODEL_URI")
    if not uri:
        logger.info(
            "Item_similarity predict skipped: ITEM_SIMILARITY_MODEL_URI is not set; set it to a model URI "
            "(e.g. runs:/<run_id>/model locally or models:/RECO_item_similarity/Production on Databricks)."
        )
        return None
    logger.info("Loading item_similarity model from {}", uri)
    model = mlflow.pyfunc.load_model(uri)
    return model


def main(model_uri: Optional[str] = None, k: int = 10) -> pd.DataFrame:
    cfg = get_config()
    logger.info(
        "Item-similarity predict: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    spark = None
    if cfg["data_source"] == "catalog" and is_running_on_databricks():
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("ItemSimilarityPredict").getOrCreate()

    apply_mlflow_config(cfg)

    model = _load_item_similarity_model(model_uri=model_uri)
    if model is None:
        return pd.DataFrame()

    data = load_reco_data(config=cfg, spark=spark)
    products = data.get("products")
    if products is None or not len(products):
        logger.warning("No products data; nothing to score.")
        if spark is not None:
            spark.stop()
        return pd.DataFrame()

    # For now, treat feature matrix as whatever build_product_feature_matrix used in training.
    # In a future iteration we can share the exact feature-engineering path.
    from use_cases.recommendation_engine.models.feature_engineering import (
        build_product_feature_matrix,
    )

    product_features, _ = build_product_feature_matrix(products)
    product_ids = product_features.index.tolist()
    query_ids = product_ids

    # pyfunc wrapper returns a DataFrame with columns:
    # product_id, similar_product_id, similarity_score, rank
    df_in = pd.DataFrame({"product_id": query_ids, "k": [k] * len(query_ids)})
    out = model.predict(df_in)

    if spark is not None and len(out):
        from pyspark.sql import functions as F

        schema = cfg["catalog_schema"]
        table = os.environ.get(
            "ITEM_SIMILARITY_TABLE",
            f"{schema}.gold_item_similarity_candidates",
        )
        logger.info("Writing item_similarity candidates to {}", table)
        sdf = spark.createDataFrame(out)
        sdf = sdf.withColumn("scored_at", F.current_timestamp())
        sdf.write.mode("overwrite").saveAsTable(table)

    if spark is not None:
        spark.stop()

    return out


if __name__ == "__main__":
    df = main()
    logger.info("Generated {} item-similarity rows", len(df))
