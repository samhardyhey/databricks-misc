"""
Job 1: Demand forecasting (reuse use_cases.demand_forecasting or run placeholder).
On Databricks: load from Unity Catalog; locally: load from CSV or sample.
"""

from pathlib import Path

from loguru import logger

from use_cases.env_utils import is_running_on_databricks


def main():
    on_databricks = is_running_on_databricks()
    spark = None
    if on_databricks:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("InventoryDemandForecasting").getOrCreate()

    try:
        # Reuse demand_forecasting use-case when available
        try:
            from use_cases.demand_forecasting.run_forecasting_experiment import (
                load_healthcare_data_from_catalog,
                load_healthcare_data_local,
                create_sample_data,
            )
            from use_cases.demand_forecasting.model_comparison import run_full_comparison

            if on_databricks and spark is not None:
                try:
                    orders_df = load_healthcare_data_from_catalog(spark)
                except Exception as e:
                    logger.warning("Catalog load failed ({}), using sample", e)
                    orders_df = create_sample_data()
            else:
                default_data_dir = Path(__file__).resolve().parents[3] / "data" / "local"
                orders_df = load_healthcare_data_local(default_data_dir)
                if orders_df is None:
                    orders_df = create_sample_data()
            run_full_comparison(
                orders_df,
                target_column="quantity",
                time_column="order_date",
                group_by=None,
                experiment_name="inventory_demand_forecast",
            )
            logger.info("Demand forecasting job completed")
        except ImportError as e:
            logger.warning("demand_forecasting not available ({}); job no-op", e)
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    main()
