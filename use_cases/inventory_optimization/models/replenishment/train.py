"""
Recompute replenishment policy (ROP, reorder quantities) as a 'train' step.

This is effectively a policy recomputation, not a learned model, but we treat it
as a retrain job for consistency with the retrain/apply taxonomy.

Intended for:
- Local runs via `python use_cases/inventory_optimization/models/replenishment/train.py`
- Databricks retrain jobs.
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
    if cfg["data_source"] == "catalog" and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("ReplenishmentTrain").getOrCreate()

    try:
        data = load_inventory_data(config=cfg, spark=spark)
        inventory = data.get("inventory")
        orders = data.get("orders")
        if (
            inventory is None
            or orders is None
            or len(inventory) == 0
            or len(orders) == 0
        ):
            logger.warning(
                "Missing inventory or orders; run data generator / medallion first"
            )
            return

        recommendations = compute_replenishment_recommendations(
            inventory,
            orders,
            lead_time_days=7.0,
            service_level=0.95,
        )
        summary = replenishment_summary(recommendations)
        logger.info("Replenishment train summary: {}", summary)
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    main()
