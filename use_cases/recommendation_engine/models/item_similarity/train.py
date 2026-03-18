"""
Train the item-to-item similarity model for the recommendation engine.

Intended for:
- Local runs via `python use_cases/recommendation_engine/models/item_similarity/train.py`
- Databricks jobs (DAB spark_python_task.python_file pointing here)

Requires [reco] extra (mlflow, lightgbm, implicit). Run: make reco-install.
"""

import tempfile
from pathlib import Path

import joblib
import mlflow
import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import (
    apply_mlflow_config,
    ensure_experiment_artifact_root,
    get_config,
)
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.evaluation import evaluate_recommendations
from use_cases.recommendation_engine.models.feature_engineering import (
    build_product_feature_matrix,
)
from use_cases.recommendation_engine.models.item_similarity.core import (
    recommend_similar_items,
    train_item_similarity,
)


def _log_item_similarity_mlflow(
    nn, scaler, product_ids: list, n_neighbors: int, metrics: dict | None = None
) -> None:
    mlflow.log_param("model_type", "item_similarity")
    mlflow.log_param("n_neighbors", n_neighbors)
    mlflow.log_param("n_products", len(product_ids))
    if metrics:
        mlflow.log_metrics(metrics)
    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
        path = f.name
    try:
        joblib.dump({"nn": nn, "scaler": scaler, "product_ids": product_ids}, path)
        mlflow.log_artifact(path, "item_similarity")
    finally:
        Path(path).unlink(missing_ok=True)
    logger.info("Logged item_similarity model and params to MLflow")


def main() -> dict:
    cfg = get_config()
    logger.info(
        "Item-similarity train: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    spark = None
    if cfg["data_source"] == "catalog" and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("ItemSimilarityTrain").getOrCreate()

    apply_mlflow_config(cfg)
    ensure_experiment_artifact_root("recommendation_engine")
    mlflow.set_experiment("recommendation_engine")
    mlflow.start_run(run_name="item_similarity_train")

    try:
        data = load_reco_data(config=cfg, spark=spark)
        interactions = data.get("interactions")
        products = data.get("products")
        if interactions is None or products is None:
            raise FileNotFoundError(
                "Need interactions and products. Local: make reco-data and set LOCAL_DATA_PATH. "
                "Catalog: ensure medallion has run (silver_reco_interactions, silver_products)."
            )

        n_neighbors = min(30, len(products))
        product_features, _ = build_product_feature_matrix(products)
        nn, scaler, product_ids = train_item_similarity(
            product_features, n_neighbors=n_neighbors
        )
        logger.info("Item similarity trained ({} products)", len(product_ids))

        # Simple hold-out evaluation on interactions (same pattern as run_reco)
        interactions = interactions.copy()
        if (
            "interaction_timestamp" not in interactions.columns
            and "timestamp" in interactions.columns
        ):
            interactions["interaction_timestamp"] = interactions["timestamp"]
        interactions = interactions.sort_values("interaction_timestamp").reset_index(
            drop=True
        )
        n = len(interactions)
        split = int(0.8 * n) if n else 0
        test_int = interactions.iloc[split:]
        test_users = test_int.groupby("customer_id")["product_id"].last().reset_index()
        test_users.columns = ["customer_id", "last_product_id"]
        preds = []
        for _, row in test_users.iterrows():
            recs = recommend_similar_items(
                nn, scaler, product_ids, product_features, row["last_product_id"], k=10
            )
            for pid, _ in recs:
                preds.append({"customer_id": row["customer_id"], "product_id": pid})
        metrics: dict = {}
        if preds:
            pred_df = pd.DataFrame(preds)
            truth = test_int[test_int["action_type"] == "purchased"][
                ["customer_id", "product_id"]
            ].drop_duplicates()
            if len(truth) and len(pred_df):
                metrics = evaluate_recommendations(pred_df, truth, k=10)
                logger.info("Metrics (item_similarity, test set): {}", metrics)

        _log_item_similarity_mlflow(
            nn, scaler, product_ids, n_neighbors, metrics=metrics
        )

        return {
            "item_similarity": True,
            "metrics": metrics,
        }
    finally:
        try:
            if mlflow.active_run():
                mlflow.end_run()
        except Exception:
            pass
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    result = main()
    logger.info("item_similarity train done: {}", result)
