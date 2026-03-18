"""
Train LightFM-based recommender for the recommendation engine.

Uses interactions from the existing loader and logs metrics / params via loguru.
"""

import tempfile

import joblib
import mlflow
from loguru import logger

from use_cases.recommendation_engine.config import (
    apply_mlflow_config,
    ensure_experiment_artifact_root,
    get_config,
)
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.lightfm.core import (
    LightFMRecoWrapper,
    train_lightfm,
)
from utils.mlflow.registry import set_latest_version_alias


def main() -> dict:
    cfg = get_config()
    logger.info(
        "LightFM train: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    spark = None
    if cfg["data_source"] == "catalog" and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("LightFMRecoTrain").getOrCreate()

    try:
        data = load_reco_data(config=cfg, spark=spark)
        interactions = data.get("interactions")
        if interactions is None or not len(interactions):
            logger.warning(
                "No interactions for LightFM. Local: make reco-data. "
                "Catalog: ensure silver_reco_interactions exists."
            )
            return {}

        # Convert interactions into the (customer_id, product_id, weight) format
        # expected by LightFM core helpers.
        df = interactions.copy()
        if "action_type" in df.columns:
            df["weight"] = (
                df["action_type"]
                .map({"purchased": 1.0, "added": 0.5, "viewed": 0.2, "searched": 0.1})
                .fillna(0.1)
                .astype(float)
            )
        else:
            df["weight"] = 1.0

        interactions_df = df[["customer_id", "product_id", "weight"]].copy()
        # LightFM core assumes string ids for mapping consistency.
        interactions_df["customer_id"] = interactions_df["customer_id"].astype(str)
        interactions_df["product_id"] = interactions_df["product_id"].astype(str)

        artifacts = train_lightfm(
            interactions_df,
            no_components=30,
            loss="warp",
            epochs=20,
            num_threads=4,
            user_col="customer_id",
            item_col="product_id",
            rating_col="weight",
        )
        logger.info(
            "LightFM trained: n_users={}, n_items={}",
            len(artifacts.user_id_map),
            len(artifacts.item_id_map),
        )
        # Log MLflow pyfunc so apply can load via `runs:/...`.
        apply_mlflow_config(cfg)
        experiment = "recommendation_engine-lightfm"
        ensure_experiment_artifact_root(experiment)
        mlflow.set_experiment(experiment)

        run = mlflow.start_run(run_name="lightfm_train")
        run_id = run.info.run_id
        try:
            with tempfile.TemporaryDirectory() as tmp:
                payload_path = f"{tmp}/lightfm_artifacts.joblib"
                joblib.dump(
                    {
                        "model": artifacts.model,
                        "user_id_map": artifacts.user_id_map,
                        "item_id_map": artifacts.item_id_map,
                        "n_items": len(artifacts.item_id_map),
                    },
                    payload_path,
                )
                mlflow.log_params(
                    {
                        "no_components": 30,
                        "loss": "warp",
                        "epochs": 20,
                        "n_users": len(artifacts.user_id_map),
                        "n_items": len(artifacts.item_id_map),
                    }
                )
                mlflow.pyfunc.log_model(
                    artifact_path="lightfm_model",
                    python_model=LightFMRecoWrapper(),
                    artifacts={"lightfm_artifacts": payload_path},
                    registered_model_name="recommendation_engine-lightfm",
                )
                set_latest_version_alias(
                    "recommendation_engine-lightfm", alias="Champion"
                )
        finally:
            mlflow.end_run()

        return {
            "n_users": len(artifacts.user_id_map),
            "n_items": len(artifacts.item_id_map),
            "run_id": run_id,
            "model_uri": f"runs:/{run_id}/lightfm_model",
        }
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    result = main()
    logger.info("LightFM train done: {}", result)
