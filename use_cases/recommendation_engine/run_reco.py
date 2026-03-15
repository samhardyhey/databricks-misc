"""
Single entrypoint for the recommendation engine: runs locally or on Databricks.
Data source is switched via config (config.get_config()): local CSV vs Unity Catalog.
- Local: RECO_DATA_SOURCE=local (default when not on Databricks); data from LOCAL_DATA_PATH / data/local.
- Databricks: RECO_DATA_SOURCE=auto (default) -> catalog when DATABRICKS_RUNTIME_VERSION is set; Spark loads from catalog.
Override with RECO_DATA_SOURCE=local|catalog|auto and RECO_CATALOG_SCHEMA, LOCAL_DATA_PATH as needed.
Run: make reco-run (local)  or  deploy as Databricks job with this script.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import get_config
from use_cases.recommendation_engine.data_loading import load_reco_data
from use_cases.recommendation_engine.feature_engineering import build_interaction_matrix, build_product_feature_matrix
from use_cases.recommendation_engine.item_similarity import recommend_similar_items, train_item_similarity
from use_cases.recommendation_engine.evaluation import evaluate_recommendations


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
        raise RuntimeError("RECO_DATA_SOURCE=catalog requires a SparkSession (e.g. on Databricks).")

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

    # --- Item similarity (Phase 1) ---
    logger.info("Building product feature matrix and training item_similarity")
    product_features, _ = build_product_feature_matrix(products)
    nn, scaler, product_ids = train_item_similarity(
        product_features, n_neighbors=min(30, len(product_features))
    )
    logger.info("Item similarity trained ({} products)", len(product_ids))

    # --- Optional ALS (Phase 2) ---
    als_model = None
    try:
        from use_cases.recommendation_engine.collaborative_filtering import train_als
        u, i, w, _, _ = build_interaction_matrix(interactions)
        als_model, _ = train_als(u, i, w, factors=32, iterations=10)
        logger.info("ALS trained")
    except ImportError:
        logger.debug("implicit not installed; skipping ALS")

    # --- Evaluate: train/test split on interactions ---
    interactions = interactions.copy()
    if "interaction_timestamp" not in interactions.columns and "timestamp" in interactions.columns:
        interactions["interaction_timestamp"] = interactions["timestamp"]
    interactions = interactions.sort_values("interaction_timestamp").reset_index(drop=True)
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
        for (pid, _) in recs:
            preds.append({"customer_id": row["customer_id"], "product_id": pid})
    metrics = {}
    if preds:
        pred_df = pd.DataFrame(preds)
        truth = test_int[test_int["action_type"] == "purchased"][["customer_id", "product_id"]].drop_duplicates()
        if len(truth) and len(pred_df):
            metrics = evaluate_recommendations(pred_df, truth, k=10)
            logger.info("Metrics (item_similarity, test set): {}", metrics)

    return {"item_similarity": True, "als": als_model is not None, "metrics": metrics}


if __name__ == "__main__":
    main()
    logger.info("reco run done")
