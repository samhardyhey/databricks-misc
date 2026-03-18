"""
Job 3: Compute replenishment recommendations (ROP, order qty); write to gold or local output.
Loads data via config: locally prefers DuckDB medallion (DBT_DUCKDB_PATH), else CSV.
"""

from loguru import logger

from use_cases.inventory_optimization.config import get_config
from use_cases.inventory_optimization.models.data_loading import load_inventory_data
from use_cases.inventory_optimization.models.evaluation import replenishment_summary
from use_cases.inventory_optimization.models.replenishment.core import (
    compute_replenishment_recommendations,
)


def main():
    cfg = get_config()
    spark = None
    if cfg["data_source"] == "catalog" and spark is None and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("ReplenishmentOptimization").getOrCreate()

    data = load_inventory_data(config=cfg, spark=spark)
    inventory = data.get("inventory")
    orders = data.get("orders")
    if inventory is None or orders is None or len(inventory) == 0 or len(orders) == 0:
        logger.warning("Missing inventory or orders; run data generator first")
        return

    recommendations = compute_replenishment_recommendations(
        inventory,
        orders,
        lead_time_days=7.0,
        service_level=0.95,
    )
    summary = replenishment_summary(recommendations)
    logger.info("Replenishment summary: {}", summary)

    if cfg["on_databricks"] and spark is not None:
        try:
            spark_df = spark.createDataFrame(recommendations)
            catalog = "workspace.healthcare_medallion"
            spark_df.write.saveAsTable(
                f"{catalog}.gold_replenishment_recommendations", mode="overwrite"
            )
            logger.info("Wrote gold_replenishment_recommendations")
        except Exception as e:
            logger.warning("Could not write to catalog: {}", e)

    if spark is not None:
        spark.stop()


if __name__ == "__main__":
    main()
