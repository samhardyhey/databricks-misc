"""
Recompute replenishment policy (ROP, reorder quantities) as a 'train' step.

This is effectively a policy recomputation, not a learned model, but we treat it
as a retrain job for consistency with the retrain/apply taxonomy.

Intended for:
- Local runs via `python use_cases/inventory_optimization/models/replenishment/train.py`
- Databricks retrain jobs.
"""

from loguru import logger

from use_cases.inventory_optimization.config import (
    apply_mlflow_config,
    ensure_experiment_artifact_root,
    get_config,
)
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

        # MLflow logging so the policy computation shows up in the UI.
        try:
            import mlflow

            apply_mlflow_config()
            experiment = "inventory_optimization-replenishment_policy"
            ensure_experiment_artifact_root(experiment)
            mlflow.set_experiment(experiment)
            with mlflow.start_run(run_name="replenishment_policy_train"):
                mlflow.log_params({"lead_time_days": 7.0, "service_level": 0.95})
                mlflow.log_metrics(summary)
        except Exception as e:
            logger.debug("MLflow logging skipped: {}", e)
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    main()
