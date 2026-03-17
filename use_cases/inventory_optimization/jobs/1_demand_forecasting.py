"""
Job 1: Demand forecasting for inventory optimisation.

This job wires the shared demand forecasting components into the
inventory use-case. On Databricks it loads from Unity Catalog;
locally it loads from CSV or sample data.
"""

from pathlib import Path

from loguru import logger

from use_cases.env_utils import is_running_on_databricks
from use_cases.inventory_optimization.data_loading import load_inventory_data
from use_cases.inventory_optimization.demand_forecasting import (
    compare_forecasting_models,
)


def main():
    on_databricks = is_running_on_databricks()
    spark = None
    if on_databricks:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("InventoryDemandForecasting").getOrCreate()

    try:
        # Reuse inventory data-loading: we need orders aggregated per product × warehouse.
        Path(__file__).resolve().parents[2]
        from use_cases.inventory_optimization.config import get_config

        cfg = get_config()
        data = load_inventory_data(config=cfg, spark=spark)
        orders = data.get("orders")
        if orders is None or len(orders) == 0:
            raise FileNotFoundError(
                "Need orders data for demand forecasting. "
                "Local: make inventory-data. Catalog: ensure silver_orders exists."
            )

        compare_forecasting_models(
            orders,
            target_column="quantity",
            time_column="order_date",
            group_by=None,
            experiment_name="inventory_demand_forecast",
        )
        logger.info("Demand forecasting job completed")
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    main()
