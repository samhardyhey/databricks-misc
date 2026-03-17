"""
Train LightFM-based recommender for the recommendation engine.

Uses interactions from the existing loader and logs metrics / params via loguru.
"""

from loguru import logger

from use_cases.recommendation_engine.config import get_config
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.feature_engineering import (
    build_interaction_matrix,
)
from use_cases.recommendation_engine.models.lightfm.core import train_lightfm


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

        # Use the same encoded user/item codes as ALS for consistency
        u, i, w, user_map, item_map = build_interaction_matrix(interactions)
        # Reconstruct a DataFrame in (customer_id, product_id) space for LightFM helpers
        inv_user = {v: k for k, v in user_map.items()}
        inv_item = {v: k for k, v in item_map.items()}
        df = (
            {
                "customer_id": inv_user[int(uu)],
                "product_id": inv_item[int(ii)],
                "weight": float(ww),
            }
            for uu, ii, ww in zip(u, i, w)
        )
        import pandas as pd

        interactions_df = pd.DataFrame(df)

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
        return {
            "n_users": len(artifacts.user_id_map),
            "n_items": len(artifacts.item_id_map),
        }
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    result = main()
    logger.info("LightFM train done: {}", result)
