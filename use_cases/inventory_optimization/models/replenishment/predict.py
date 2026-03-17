"""
Batch apply replenishment optimisation and write recommendations.

Intended for:
- Local runs via `python use_cases/inventory_optimization/models/replenishment/predict.py`
- Databricks apply jobs (gold_replenishment_recommendations).
"""

import os

from loguru import logger

from use_cases.inventory_optimization.config import get_config
from use_cases.inventory_optimization.data_loading import load_inventory_data
from use_cases.inventory_optimization.evaluation import replenishment_summary
from use_cases.inventory_optimization.replenishment_optimizer import (
    compute_replenishment_recommendations,
)
from use_cases.env_utils import is_running_on_databricks


def main():
    cfg = get_config()
    spark = None
    if cfg["data_source"] == "catalog" and is_running_on_databricks():
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("ReplenishmentApply").getOrCreate()

    try:
        data = load_inventory_data(config=cfg, spark=spark)
        inventory = data.get("inventory")
        orders = data.get("orders")
        if inventory is None or orders is None or len(inventory) == 0 or len(orders) == 0:
            logger.warning("Missing inventory or orders; nothing to apply.")
            return

        recommendations = compute_replenishment_recommendations(
            inventory,
            orders,
            lead_time_days=7.0,
            service_level=0.95,
        )
        summary = replenishment_summary(recommendations)
        logger.info("Replenishment apply summary: {}", summary)

        if spark is not None:
            from pyspark.sql import functions as F

            schema = cfg["catalog_schema"]
            table = os.environ.get(
                "REPLENISHMENT_TABLE",
                f"{schema}.gold_replenishment_recommendations",
            )
            logger.info("Writing replenishment recommendations to {}", table)
            sdf = spark.createDataFrame(recommendations)
            sdf = sdf.withColumn("computed_at", F.current_timestamp())
            sdf.write.mode("overwrite").saveAsTable(table)
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    main()

