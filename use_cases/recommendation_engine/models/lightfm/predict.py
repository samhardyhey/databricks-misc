"""
Batch apply LightFM-based recommender for a set of users.

Current behaviour:
- Trains (or reloads) a LightFM model and scores a provided list of user_ids.
- Designed to be called from jobs or locally; can be extended to write to UC tables.
"""

import os
from typing import Optional

import mlflow
import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import apply_mlflow_config, get_config
from use_cases.recommendation_engine.models.data_loading import load_reco_data


def _load_lightfm_model(model_uri: Optional[str] = None):
    uri = (
        model_uri
        or os.environ.get("LIGHTFM_MODEL_URI")
        or "models:/recommendation_engine-lightfm@Champion"
    )
    if not uri:
        logger.info(
            "LightFM predict skipped: LIGHTFM_MODEL_URI is not set (or pass model_uri)."
        )
        return None
    logger.info("Loading LightFM model from {}", uri)
    return mlflow.pyfunc.load_model(uri)


def main(
    user_ids: Optional[list[str]] = None,
    k: int = 10,
    model_uri: Optional[str] = None,
) -> pd.DataFrame:
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
        apply_mlflow_config(cfg)
        model = _load_lightfm_model(model_uri=model_uri)
        if model is None:
            return pd.DataFrame()

        data = load_reco_data(config=cfg, spark=spark)
        interactions = data.get("interactions")
        if interactions is None or not len(interactions):
            logger.warning("No interactions for LightFM predict; nothing to score.")
            return pd.DataFrame()

        # Choose users to score
        if user_ids is None:
            # If ALS user coding exists, we could re-use, but here we simply use raw ids
            user_ids = interactions["customer_id"].astype(str).unique().tolist()[:100]

        df_in = pd.DataFrame(
            {
                "customer_id": user_ids,
                "k": [int(k)] * len(user_ids),
            }
        )
        recs = model.predict(df_in)
        logger.info("Generated {} LightFM recommendations", len(recs))
        return recs
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    df = main()
    logger.info("LightFM predictions for {} rows", len(df))
