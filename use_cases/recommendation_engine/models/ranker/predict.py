"""
Apply LightGBM ranker for recommendation_engine.
"""

import os

import mlflow.lightgbm
import pandas as pd
from loguru import logger
from mlflow.exceptions import MlflowException

from use_cases.recommendation_engine.config import apply_mlflow_config, get_config
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.feature_engineering import add_negative_samples
from use_cases.recommendation_engine.models.ranker.core import rank_candidates


def _build_candidate_frame(training_base: pd.DataFrame, products: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    sampled = add_negative_samples(training_base, products, n_neg_per_pos=2)
    merged = sampled.merge(products, on="product_id", how="left")
    feature_cols: list[str] = []
    for col in merged.columns:
        if col in {
            "customer_id",
            "product_id",
            "label",
            "last_interaction_timestamp",
            "interaction_timestamp",
            "timestamp",
        }:
            continue
        if merged[col].dtype == object:
            merged[col] = pd.factorize(merged[col].fillna(""))[0]
        else:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
        feature_cols.append(col)
    return merged, feature_cols


def main(model_uri: str | None = None, top_k: int = 10) -> pd.DataFrame:
    cfg = get_config()
    logger.info(
        "Ranker apply: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )
    apply_mlflow_config(cfg)

    spark = None
    if cfg["data_source"] == "catalog" and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("RecoRankerApply").getOrCreate()

    try:
        data = load_reco_data(config=cfg, spark=spark)
        training_base = data.get("training_base")
        products = data.get("products")
        if training_base is None or products is None or training_base.empty:
            raise RuntimeError(
                "Missing training_base/products for ranker apply. "
                "Local: run make reco-local-data && make reco-build-training-base."
            )

        uri = (
            model_uri
            or os.environ.get("RECO_RANKER_MODEL_URI")
            or "models:/recommendation_engine-ranker@Champion"
        )
        logger.info("Loading ranker model from {}", uri)
        try:
            model = mlflow.lightgbm.load_model(uri)
        except MlflowException as e:
            logger.info("Ranker apply skipped: could not load model from '{}': {}", uri, e)
            return pd.DataFrame()

        candidates, feature_cols = _build_candidate_frame(training_base, products)
        out = rank_candidates(model, candidates, feature_cols, top_k=top_k)
        logger.info("Generated {} ranker recommendations", len(out))
        return out
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    frame = main()
    logger.info("Ranker apply done: rows={}", len(frame))
