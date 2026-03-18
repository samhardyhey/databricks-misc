"""
Train the inventory write-off risk classifier as a standalone entrypoint.

Intended for:
- Local runs via `python use_cases/inventory_optimization/models/writeoff_risk/train.py`
- Databricks jobs (DAB spark_python_task.python_file pointing here)

Behaviour:
- Uses inventory_optimization.config.get_config() for local vs catalog and schema.
- Loads data via load_inventory_data (same as run_inventory_smoke.py / jobs/2_writeoff_risk_model.py).
- Builds features with build_writeoff_risk_features and trains a classifier.
- Logs metrics and model to MLflow when available.
"""

from loguru import logger

from use_cases.inventory_optimization.config import (
    apply_mlflow_config,
    ensure_experiment_artifact_root,
    get_config,
)
from use_cases.inventory_optimization.models.data_loading import load_inventory_data
from use_cases.inventory_optimization.models.writeoff_risk.core import (
    build_writeoff_risk_features,
    train_writeoff_risk_classifier,
)


def main() -> dict:
    cfg = get_config()
    spark = None
    if cfg["data_source"] == "catalog" and spark is None and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("WriteoffRiskTrain").getOrCreate()

    data = load_inventory_data(config=cfg, spark=spark)
    inventory = data.get("inventory")
    orders = data.get("orders")
    products = data.get("products")
    if inventory is None or len(inventory) == 0:
        logger.warning("No inventory data; run data generator / medallion first")
        if spark is not None:
            spark.stop()
        return {"writeoff_risk_trained": False, "reason": "no_inventory"}

    features_df = build_writeoff_risk_features(
        inventory, orders=orders, products=products
    )
    if "days_until_expiry" in features_df.columns:
        features_df["will_expire_30d"] = (
            (features_df["days_until_expiry"] >= 0)
            & (features_df["days_until_expiry"] <= 30)
        ).astype(int)
    else:
        features_df["will_expire_30d"] = 0

    if features_df["will_expire_30d"].sum() < 5:
        logger.warning("Insufficient positive labels for write-off classifier")
        if spark is not None:
            spark.stop()
        return {
            "writeoff_risk_trained": False,
            "reason": "insufficient_positive_labels",
        }

    model, feature_cols, metrics = train_writeoff_risk_classifier(features_df)
    logger.info("Write-off risk model trained: {}", metrics)

    # MLflow logging (local and Databricks) so make mlflow-ui shows all models
    import mlflow
    import mlflow.sklearn

    apply_mlflow_config()
    experiment = "inventory_optimization-writeoff_risk"
    ensure_experiment_artifact_root(experiment)
    mlflow.set_experiment(experiment)

    run = mlflow.start_run(run_name="writeoff_risk_classifier")
    run_id = run.info.run_id
    try:
        mlflow.log_params(
            {
                "n_features": len(feature_cols),
                "features": ",".join(feature_cols),
            }
        )
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(model, "model")
    finally:
        mlflow.end_run()

    logger.info("Logged write-off risk model to MLflow")

    if spark is not None:
        spark.stop()

    return {
        "writeoff_risk_trained": True,
        "run_id": run_id,
        "model_uri": f"runs:/{run_id}/model",
        "metrics": metrics,
    }


if __name__ == "__main__":
    main()
