"""
Train the ALS collaborative filtering model for the recommendation engine.

Intended for:
- Local runs via `python use_cases/recommendation_engine/models/als/train.py`
- Databricks jobs (ALS retrain).

Requires the [reco] extra (implicit, lightgbm, mlflow). Run: make reco-install.
"""

import mlflow
from loguru import logger

from use_cases.recommendation_engine.config import apply_mlflow_config, get_config
from use_cases.recommendation_engine.models.als.core import train_als
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.feature_engineering import (
    build_interaction_matrix,
)


def main() -> dict:
    cfg = get_config()
    logger.info(
        "ALS train: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    spark = None
    if cfg["data_source"] == "catalog" and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("ALSRecoTrain").getOrCreate()

    apply_mlflow_config(cfg)
    mlflow.set_experiment("recommendation_engine")
    if mlflow.active_run() is None:
        mlflow.start_run(run_name="reco_als_pipeline")

    try:
        data = load_reco_data(config=cfg, spark=spark)
        interactions = data.get("interactions")
        if interactions is None or not len(interactions):
            raise FileNotFoundError(
                "Need interactions for ALS. Local: make reco-data. "
                "Catalog: ensure silver_reco_interactions exists."
            )

        user_ids, item_ids, weights, _, _ = build_interaction_matrix(interactions)
        model, user_item_matrix = train_als(
            user_ids,
            item_ids,
            weights,
            factors=32,
            iterations=10,
            log_to_mlflow=True,
            artifact_path="als_model",
        )
        logger.info(
            "ALS model trained: n_users={}, n_items={}",
            user_item_matrix.shape[0],
            user_item_matrix.shape[1],
        )
        return {
            "als_trained": True,
            "n_users": int(user_item_matrix.shape[0]),
            "n_items": int(user_item_matrix.shape[1]),
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
    logger.info("ALS train done: {}", result)

