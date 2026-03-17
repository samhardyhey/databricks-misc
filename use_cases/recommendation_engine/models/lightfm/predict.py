"""
Batch apply LightFM-based recommender for a set of users.

Current behaviour:
- Trains (or reloads) a LightFM model and scores a provided list of user_ids.
- Designed to be called from jobs or locally; can be extended to write to UC tables.
"""

import os
from typing import Optional

import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import get_config
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.feature_engineering import (
    build_interaction_matrix,
)
from use_cases.recommendation_engine.models.lightfm.core import (
    LightFMArtifacts,
    recommend_for_users,
    train_lightfm,
)


def _train_or_load_lightfm(interactions: pd.DataFrame) -> LightFMArtifacts:
    """
    For now we train a fresh LightFM model; this can be extended
    later to load from persisted MLflow artifacts.
    """
    return train_lightfm(
        interactions,
        no_components=30,
        loss="warp",
        epochs=10,
        num_threads=4,
        user_col="customer_id",
        item_col="product_id",
        rating_col=None,
    )


def main(user_ids: Optional[list[str]] = None, k: int = 10) -> pd.DataFrame:
    cfg = get_config()
    logger.info(
        "LightFM predict: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    spark = None
    if cfg["data_source"] == "catalog" and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("LightFMRecoPredict").getOrCreate()

    try:
        data = load_reco_data(config=cfg, spark=spark)
        interactions = data.get("interactions")
        if interactions is None or not len(interactions):
            logger.warning("No interactions for LightFM predict; nothing to score.")
            return pd.DataFrame()

        # Choose users to score
        if user_ids is None:
            # If ALS user coding exists, we could re-use, but here we simply use raw ids
            user_ids = (
                interactions["customer_id"].astype(str).unique().tolist()[:100]
            )

        artifacts = _train_or_load_lightfm(interactions)
        recs = recommend_for_users(artifacts, user_ids=user_ids, k=k)
        logger.info("Generated {} LightFM recommendations", len(recs))
        return recs
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    df = main()
    logger.info("LightFM predictions for {} rows", len(df))

