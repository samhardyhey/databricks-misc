"""
Train a LightGBM ranker for recommendation_engine.
"""

import pandas as pd
import mlflow
from loguru import logger

from use_cases.recommendation_engine.config import (
    apply_mlflow_config,
    ensure_experiment_artifact_root,
    get_config,
)
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.feature_engineering import add_negative_samples
from use_cases.recommendation_engine.models.ranker.core import train_ranker
from utils.mlflow.registry import set_latest_version_alias


def _build_ranker_frame(
    training_base: pd.DataFrame, products: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    df = training_base.copy()
    if "label" not in df.columns:
        df["label"] = 1

    merged = df.merge(products, on="product_id", how="left")

    # Build a simple numeric feature set for ranker baseline.
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


def main() -> dict:
    cfg = get_config()
    logger.info(
        "Ranker train: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    spark = None
    if cfg["data_source"] == "catalog" and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("RecoRankerTrain").getOrCreate()

    try:
        data = load_reco_data(config=cfg, spark=spark)
        training_base = data.get("training_base")
        products = data.get("products")
        if training_base is None or products is None or training_base.empty:
            raise RuntimeError(
                "Missing training_base/products for ranker training. "
                "Local: run make reco-local-data && make reco-build-training-base."
            )

        sampled = add_negative_samples(training_base, products, n_neg_per_pos=2)
        train_df, feature_cols = _build_ranker_frame(sampled, products)

        apply_mlflow_config(cfg)
        experiment = "recommendation_engine-ranker"
        ensure_experiment_artifact_root(experiment)
        mlflow.set_experiment(experiment)

        with mlflow.start_run(run_name="ranker_train") as run:
            model = train_ranker(
                train_df=train_df,
                feature_cols=feature_cols,
                group_col="customer_id",
                label_col="label",
                log_to_mlflow=False,
            )
            mlflow.log_param("n_features", len(feature_cols))
            mlflow.log_param("n_rows", len(train_df))
            mlflow.lightgbm.log_model(
                model.booster_,
                artifact_path="ranker_model",
                registered_model_name="recommendation_engine-ranker",
            )
            set_latest_version_alias("recommendation_engine-ranker", alias="Champion")

        model_uri = f"runs:/{run.info.run_id}/ranker_model"
        logger.info("Ranker trained; model_uri={}", model_uri)
        return {"model_uri": model_uri, "n_rows": len(train_df), "n_features": len(feature_cols)}
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    result = main()
    logger.info("Ranker train done: {}", result)
