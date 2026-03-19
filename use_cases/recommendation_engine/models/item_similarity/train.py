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
from use_cases.recommendation_engine.models.feature_engineering import (
    build_product_feature_matrix,
)
from use_cases.recommendation_engine.models.reco_split_eval import (
    RECOMMENDATION_OFFLINE_EVAL_K,
    DEFAULT_VAL_FRACTION,
    log_common_reco_eval_params_mlflow,
    offline_max_eval_users,
    purchases_truth,
    standard_offline_metrics,
    temporal_train_val_split,
    evaluate_prediction_df,
)
from use_cases.recommendation_engine.models.item_similarity.core import (
    ItemSimilarityRecoWrapper,
    recommend_similar_items,
    train_item_similarity,
)
from utils.mlflow.registry import set_latest_version_alias


def _log_item_similarity_mlflow(
    nn,
    scaler,
    product_features: pd.DataFrame,
    product_ids: list,
    n_neighbors: int,
    metrics: dict | None = None,
) -> None:
    mlflow.log_param("model_type", "item_similarity")
    mlflow.log_param("n_neighbors", n_neighbors)
    mlflow.log_param("n_products", len(product_ids))
    if metrics:
        mlflow.log_metrics(metrics)
    # Log as MLflow pyfunc so apply can load via mlflow.pyfunc.load_model.
    with tempfile.TemporaryDirectory() as tmp:
        payload_path = Path(tmp) / "item_similarity.joblib"
        joblib.dump(
            {
                "nn": nn,
                "scaler": scaler,
                "product_features": product_features,
                "product_ids": product_ids,
            },
            payload_path,
        )
        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=ItemSimilarityRecoWrapper(),
            artifacts={"item_similarity": str(payload_path)},
            registered_model_name="recommendation_engine-item_similarity",
        )
        set_latest_version_alias(
            "recommendation_engine-item_similarity", alias="Champion"
        )
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
    ensure_experiment_artifact_root("recommendation_engine-item_similarity")
    mlflow.set_experiment("recommendation_engine-item_similarity")
    run = mlflow.start_run(run_name="item_similarity_train")
    run_id = run.info.run_id

    try:
        data = load_reco_data(config=cfg, spark=spark)
        interactions = data.get("interactions")
        products = data.get("products")
        if interactions is None or products is None:
            raise FileNotFoundError(
                "Need interactions and products. Local: make reco-data and set LOCAL_DATA_PATH. "
                "Catalog: ensure medallion has run (silver_reco_interactions, silver_products)."
            )

        train_int, val_int = temporal_train_val_split(
            interactions, val_fraction=DEFAULT_VAL_FRACTION
        )

        n_neighbors = min(30, len(products))
        product_features, _ = build_product_feature_matrix(products)
        nn, scaler, product_ids = train_item_similarity(
            product_features, n_neighbors=n_neighbors
        )
        logger.info("Item similarity trained ({} products)", len(product_ids))

        k = RECOMMENDATION_OFFLINE_EVAL_K
        ts_col = (
            "interaction_timestamp"
            if "interaction_timestamp" in train_int.columns
            else "timestamp"
        )
        train_sorted = train_int.sort_values(ts_col).reset_index(drop=True)
        last_train_product = (
            train_sorted.groupby("customer_id")["product_id"].last().reset_index()
        )
        last_train_product.columns = ["customer_id", "anchor_product_id"]
        last_train_product["customer_id"] = last_train_product["customer_id"].astype(
            str
        )
        truth = purchases_truth(val_int)
        anchors = last_train_product[
            last_train_product["customer_id"].isin(truth["customer_id"])
        ].drop_duplicates(subset=["customer_id"])
        max_u = offline_max_eval_users()
        if max_u > 0 and len(anchors) > max_u:
            anchors = anchors.iloc[:max_u]
        preds = []
        for _, row in anchors.iterrows():
            recs = recommend_similar_items(
                nn,
                scaler,
                product_ids,
                product_features,
                row["anchor_product_id"],
                k=k,
            )
            for pid, _ in recs:
                preds.append(
                    {
                        "customer_id": str(row["customer_id"]),
                        "product_id": str(pid),
                    }
                )
        metrics: dict[str, float] = standard_offline_metrics(
            {"precision_at_k": 0.0, "recall_at_k": 0.0, "ndcg_at_k": 0.0}
        )
        if preds:
            pred_df = pd.DataFrame(preds)
            raw = evaluate_prediction_df(pred_df, truth, k=k)
            metrics = standard_offline_metrics(raw)
            logger.info("Metrics (item_similarity, temporal val): {}", metrics)

        if mlflow.active_run() is not None:
            mlflow.log_params(
                log_common_reco_eval_params_mlflow(
                    DEFAULT_VAL_FRACTION,
                    k,
                    len(train_int),
                    len(val_int),
                )
            )

        _log_item_similarity_mlflow(
            nn,
            scaler,
            product_features,
            product_ids,
            n_neighbors,
            metrics=metrics or None,
        )

        return {
            "item_similarity": True,
            "metrics": metrics,
            "run_id": run_id,
            "model_uri": f"runs:/{run_id}/model",
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
