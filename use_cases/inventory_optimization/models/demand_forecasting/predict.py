"""
Batch apply demand forecasting model(s) to generate a forecast series.

Current behaviour:
- Reuses compare_forecasting_models to run experiments and returns test forecasts;
  in future this can be extended to load a chosen production model and write
  a gold_demand_forecast table.

Intended for:
- Local exploration via `python use_cases/inventory_optimization/models/demand_forecasting/predict.py`
- Databricks jobs once a stable production forecaster is selected.
"""

from loguru import logger

from use_cases.env_utils import is_running_on_databricks
from use_cases.inventory_optimization.config import get_config
from use_cases.inventory_optimization.models.data_loading import load_inventory_data
from use_cases.inventory_optimization.models.demand_forecasting.core import (
    compare_forecasting_models,
)


def main():
    cfg = get_config()
    on_databricks = is_running_on_databricks()
    spark = None
    if cfg["data_source"] == "catalog" and on_databricks:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName(
            "InventoryDemandForecastingApply"
        ).getOrCreate()

    try:
        data = load_inventory_data(config=cfg, spark=spark)
        orders = data.get("orders")
        if orders is None or len(orders) == 0:
            logger.warning(
                "No orders data for demand forecasting apply. "
                "Local: make inventory-data. Catalog: ensure silver_orders exists."
            )
            return {}

        results = compare_forecasting_models(
            orders,
            target_column="quantity",
            time_column="order_date",
            group_by=None,
            experiment_name="inventory_demand_forecast_apply",
        )
        logger.info(
            "Demand forecasting apply completed; comparison summary keys: {}",
            list(results.get("comparison_summary", {}).keys()),
        )
        return results
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    main()
