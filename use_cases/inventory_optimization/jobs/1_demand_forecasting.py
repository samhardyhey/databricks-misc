"""
Job 1: Demand forecasting for inventory optimisation.

Loads data via config: Unity Catalog on Databricks; locally prefers DuckDB medallion
(DBT_DUCKDB_PATH) with CSV fallback. Uses the same medallion we create (make data-local-dbt-run).
"""

from loguru import logger

from use_cases.inventory_optimization.config import apply_mlflow_config, get_config
from use_cases.inventory_optimization.models.data_loading import load_inventory_data
from use_cases.inventory_optimization.models.demand_forecasting.core import (
    compare_forecasting_models,
)
from utils.env_utils import is_running_on_databricks


def main():
    on_databricks = is_running_on_databricks()
    spark = None
    if on_databricks:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("InventoryDemandForecasting").getOrCreate()

    try:
        cfg = get_config()
        data = load_inventory_data(config=cfg, spark=spark)
        orders = data.get("orders")
        if orders is None or len(orders) == 0:
            raise FileNotFoundError(
                "Need orders data for demand forecasting. "
                "Local: make inventory-data. Catalog: ensure silver_orders exists."
            )

        apply_mlflow_config()
        compare_forecasting_models(
            orders,
            target_column="quantity",
            time_column="order_date",
            group_by=None,
            experiment_name="inventory_optimization-demand_forecast",
        )
        logger.info("Demand forecasting job completed")
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    main()
