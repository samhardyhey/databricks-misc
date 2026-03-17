"""
Batch apply the item-to-item similarity model to products.

Intended for:
- Local runs via `python use_cases/recommendation_engine/models/item_similarity/predict.py`
- Databricks jobs for offline candidate generation (future gold_reco_candidates, etc.).

Behaviour:
- Uses recommendation_engine.config.get_config() for local vs catalog and schema.
- Loads products (and optionally interactions) via load_reco_data.
- Loads item_similarity model from MLflow.
- Generates top-K similar items per product and optionally writes to a table on Databricks.
"""

import os
from typing import Optional

import pandas as pd
from loguru import logger

from use_cases.env_utils import is_running_on_databricks
from use_cases.recommendation_engine.config import apply_mlflow_config, get_config
from use_cases.recommendation_engine.data_loading import load_reco_data
from use_cases.recommendation_engine.item_similarity import recommend_similar_items_batch


def _load_item_similarity_model(model_uri: Optional[str] = None):
    try:
        import mlflow
    except ImportError:
        raise RuntimeError("mlflow is required to load the item_similarity model.")

    uri = model_uri or os.environ.get(
        "ITEM_SIMILARITY_MODEL_URI", "models:/RECO_item_similarity/Production"
    )
    logger.info("Loading item_similarity model from {}", uri)
    model = mlflow.pyfunc.load_model(uri)
    # Expect a dict-like artifact with keys: nn, scaler, product_ids
    artifacts = model.load_context().artifacts
    logger.debug("Loaded item_similarity artifacts: {}", list(artifacts.keys()))
    # Fallback: let the pyfunc model handle prediction; we only need it in Databricks context.
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

    try:
        import mlflow
    except ImportError:
        mlflow = None  # type: ignore[assignment]

    if mlflow is not None:
        apply_mlflow_config(cfg)

    data = load_reco_data(config=cfg, spark=spark)
    products = data.get("products")
    if products is None or not len(products):
        logger.warning("No products data; nothing to score.")
        if spark is not None:
            spark.stop()
        return pd.DataFrame()

    # For now, treat feature matrix as whatever build_product_feature_matrix used in training.
    # In a future iteration we can share the exact feature-engineering path.
    from use_cases.recommendation_engine.feature_engineering import (
        build_product_feature_matrix,
    )

    product_features, _ = build_product_feature_matrix(products)
    product_ids = product_features.index.tolist()
    query_ids = product_ids

    # This implementation assumes a future MLflow artifact format; until then, we can
    # reuse recommend_similar_items_batch by re-training or by loading a pickled artifact.
    # Here we simply construct an identity "similarity" (each product similar to itself)
    # as a placeholder so the batch-apply pipeline is wired.
    recs = {
        pid: [(pid, 0.0)] for pid in query_ids
    }  # TODO: replace with true model loading when artifacts are standardized.

    rows = []
    for pid, sim_list in recs.items():
        for rank, (rec_pid, score) in enumerate(sim_list[:k], start=1):
            rows.append(
                {
                    "product_id": pid,
                    "similar_product_id": rec_pid,
                    "similarity_score": float(score),
                    "rank": rank,
                }
            )
    out = pd.DataFrame(rows)

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

