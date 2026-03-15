"""
Job 3: Compute replenishment recommendations (ROP, order qty); write to gold or local output.
"""

from loguru import logger

from use_cases.env_utils import is_running_on_databricks
from use_cases.inventory_optimization.data_loading import get_inventory_data
from use_cases.inventory_optimization.replenishment_optimizer import (
    compute_replenishment_recommendations,
)
from use_cases.inventory_optimization.evaluation import replenishment_summary


def main():
    on_databricks = is_running_on_databricks()
    spark = None
    if on_databricks:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("ReplenishmentOptimization").getOrCreate()

    data = get_inventory_data(spark)
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

    if on_databricks and spark is not None:
        try:
            spark_df = spark.createDataFrame(recommendations)
            catalog = "workspace.healthcare_medallion"
            spark_df.write.saveAsTable(f"{catalog}.gold_replenishment_recommendations", mode="overwrite")
            logger.info("Wrote gold_replenishment_recommendations")
        except Exception as e:
            logger.warning("Could not write to catalog: {}", e)

    if spark is not None:
        spark.stop()


if __name__ == "__main__":
    main()
