"""
Batch apply replenishment optimisation and write recommendations.

Intended for:
- Local runs via `python use_cases/inventory_optimization/models/replenishment/predict.py`
- Databricks apply jobs (gold_replenishment_recommendations).
"""

import os

from loguru import logger

from use_cases.inventory_optimization.config import get_config
from use_cases.inventory_optimization.models.data_loading import load_inventory_data
from use_cases.inventory_optimization.models.evaluation import replenishment_summary
from use_cases.inventory_optimization.models.replenishment.core import (
    compute_replenishment_recommendations,
)
from utils.env_utils import is_running_on_databricks


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
        if (
            inventory is None
            or orders is None
            or len(inventory) == 0
            or len(orders) == 0
        ):
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

        # MLflow logging for the apply step (useful in local runs where we want visibility).
        try:
            import mlflow

            from use_cases.inventory_optimization.config import (
                apply_mlflow_config,
                ensure_experiment_artifact_root,
            )

            apply_mlflow_config()
            # Apply step metrics are still for the same replenishment policy model.
            experiment = "inventory_optimization-replenishment_policy"
            ensure_experiment_artifact_root(experiment)
            mlflow.set_experiment(experiment)
            with mlflow.start_run(run_name="replenishment_policy_apply"):
                mlflow.log_params({"lead_time_days": 7.0, "service_level": 0.95})
                mlflow.log_metrics(summary)
        except Exception as e:
            logger.debug("MLflow logging skipped: {}", e)

        if spark is not None:
            from pyspark.sql import functions as F

            schema = cfg["output_schema"]
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
