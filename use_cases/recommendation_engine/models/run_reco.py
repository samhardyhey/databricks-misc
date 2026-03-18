"""
Single entrypoint for the recommendation engine: runs locally or on Databricks.
Data source is switched via config (config.get_config()): local CSV vs Unity Catalog.
Requires [reco] extra (implicit, lightgbm, mlflow). Run: make reco-install.
- Local: RECO_DATA_SOURCE=local (default when not on Databricks); data from LOCAL_DATA_PATH / data/local.
- Databricks: RECO_DATA_SOURCE=auto (default) -> catalog when DATABRICKS_RUNTIME_VERSION is set; Spark loads from catalog.
Override with RECO_DATA_SOURCE=local|catalog|auto and RECO_CATALOG_SCHEMA, LOCAL_DATA_PATH as needed.
Run: make reco-install && make reco-run (local)  or  deploy as Databricks job with this script.
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
from use_cases.recommendation_engine.models.als.core import train_als
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.evaluation import evaluate_recommendations
from use_cases.recommendation_engine.models.feature_engineering import (
    build_interaction_matrix,
    build_product_feature_matrix,
)
from use_cases.recommendation_engine.models.item_similarity.core import (
    recommend_similar_items,
    train_item_similarity,
)


def _log_item_similarity_mlflow(
    nn, scaler, product_ids: list, n_neighbors: int, metrics: dict | None = None
) -> None:
    """Log item_similarity model (nn, scaler, product_ids) and optional metrics to active MLflow run."""
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


def main(config: dict | None = None, spark=None) -> dict:
    """
    Load data (from config: local or catalog), train item_similarity + optional ALS, evaluate.
    config: from get_config() if None. spark: required when config["data_source"] == "catalog".
    """
    cfg = config or get_config()
    logger.info(
        "Reco run: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )
    if cfg["data_source"] == "catalog" and spark is None and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("RecoRun").getOrCreate()
    elif cfg["data_source"] == "catalog" and spark is None:
        raise RuntimeError(
            "RECO_DATA_SOURCE=catalog requires a SparkSession (e.g. on Databricks)."
        )

    apply_mlflow_config()
    ensure_experiment_artifact_root("recommendation_engine")
    mlflow.set_experiment("recommendation_engine")
    mlflow.start_run(run_name="reco_pipeline")

    try:
        data = load_reco_data(config=cfg, spark=spark)
        interactions = data.get("interactions")
        products = data.get("products")
        training_base = data.get("training_base")
        if interactions is None or products is None:
            raise FileNotFoundError(
                "Need interactions and products. Local: make reco-data and set LOCAL_DATA_PATH. "
                "Catalog: ensure medallion has run (silver_reco_interactions, silver_products)."
            )
        if training_base is None:
            training_base = data.get("training_base")
        if training_base is None and interactions is not None:
            training_base = data["training_base"]  # built by loader
        if training_base is None:
            raise FileNotFoundError("training_base missing from loader output.")

        n_neighbors = min(30, len(products))
        # --- Item similarity (Phase 1) ---
        logger.info("Building product feature matrix and training item_similarity")
        product_features, _ = build_product_feature_matrix(products)
        nn, scaler, product_ids = train_item_similarity(
            product_features, n_neighbors=n_neighbors
        )
        logger.info("Item similarity trained ({} products)", len(product_ids))

        # --- ALS (Phase 2) ---
        u, i, w, _, _ = build_interaction_matrix(interactions)
        als_model, _ = train_als(u, i, w, factors=32, iterations=10, log_to_mlflow=True)
        logger.info("ALS trained")

        # --- Evaluate: train/test split on interactions ---
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
        metrics = {}
        if preds:
            pred_df = pd.DataFrame(preds)
            truth = test_int[test_int["action_type"] == "purchased"][
                ["customer_id", "product_id"]
            ].drop_duplicates()
            if len(truth) and len(pred_df):
                metrics = evaluate_recommendations(pred_df, truth, k=10)
                logger.info("Metrics (item_similarity, test set): {}", metrics)

        # --- MLflow: log item_similarity artifact and eval metrics ---
        _log_item_similarity_mlflow(
            nn, scaler, product_ids, n_neighbors, metrics=metrics
        )

        return {
            "item_similarity": True,
            "als": True,
            "metrics": metrics,
        }
    finally:
        try:
            if mlflow.active_run():
                mlflow.end_run()
        except Exception:
            pass


if __name__ == "__main__":
    main()
    logger.info("reco run done")
