"""
Train demand forecasting models for inventory optimisation.

Intended for:
- Local runs via `python use_cases/inventory_optimization/models/demand_forecasting/train.py`
- Databricks jobs (spark_python_task.python_file pointing here).

Behaviour:
- Uses inventory_optimization.config.get_config() for local vs catalog and schema.
- Loads orders via load_inventory_data.
- Runs compare_forecasting_models to train/evaluate multiple forecasters and log to MLflow.
"""

from loguru import logger

from use_cases.env_utils import is_running_on_databricks
from use_cases.inventory_optimization.config import get_config
from use_cases.inventory_optimization.models.data_loading import load_inventory_data
from use_cases.inventory_optimization.models.demand_forecasting.core import (
    compare_forecasting_models,
)


def main() -> None:
    cfg = get_config()
    on_databricks = is_running_on_databricks()
    spark = None
    if cfg["data_source"] == "catalog" and on_databricks:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("InventoryDemandForecastingTrain").getOrCreate()

    try:
        data = load_inventory_data(config=cfg, spark=spark)
        orders = data.get("orders")
        if orders is None or len(orders) == 0:
            logger.warning(
                "No orders data for demand forecasting. "
                "Local: make inventory-data. Catalog: ensure silver_orders exists."
            )
            return

        compare_forecasting_models(
            orders,
            target_column="quantity",
            time_column="order_date",
            group_by=None,
            experiment_name="inventory_demand_forecast",
        )
        logger.info("Demand forecasting training/comparison completed.")
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    main()

