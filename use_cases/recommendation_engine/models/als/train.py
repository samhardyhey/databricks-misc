"""
Train the ALS collaborative filtering model for the recommendation engine.

Intended for:
- Local runs via `python use_cases/recommendation_engine/models/als/train.py`
- Databricks jobs (ALS retrain).

Requires the [reco] extra (implicit, lightgbm, mlflow). Run: make reco-install.
"""

import mlflow
import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import (
    apply_mlflow_config,
    ensure_experiment_artifact_root,
    get_config,
)
from use_cases.recommendation_engine.models.als.core import recommend_als, train_als
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.feature_engineering import (
    build_interaction_matrix,
)
from use_cases.recommendation_engine.models.reco_split_eval import (
    RECOMMENDATION_OFFLINE_EVAL_K,
    DEFAULT_VAL_FRACTION,
    log_common_reco_eval_params_mlflow,
    offline_max_eval_users,
    purchases_truth,
    standard_offline_metrics,
    temporal_train_val_split,
    evaluate_prediction_df,
)


def main() -> dict:
    cfg = get_config()
    logger.info(
        "ALS train: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    spark = None
    if cfg["data_source"] == "catalog" and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("ALSRecoTrain").getOrCreate()

    apply_mlflow_config(cfg)
    ensure_experiment_artifact_root("recommendation_engine-als")
    mlflow.set_experiment("recommendation_engine-als")
    run = mlflow.active_run()
    if run is None:
        run = mlflow.start_run(run_name="als_train")
    run_id = run.info.run_id

    try:
        data = load_reco_data(config=cfg, spark=spark)
        interactions = data.get("interactions")
        if interactions is None or not len(interactions):
            raise FileNotFoundError(
                "Need interactions for ALS. Local: make reco-data. "
                "Catalog: ensure silver_reco_interactions exists."
            )

        train_int, val_int = temporal_train_val_split(
            interactions, val_fraction=DEFAULT_VAL_FRACTION
        )
        user_ids, item_ids, weights, cust_cat, prod_cat = build_interaction_matrix(
            train_int
        )
        model, user_item_matrix = train_als(
            user_ids,
            item_ids,
            weights,
            factors=32,
            iterations=10,
            log_to_mlflow=True,
            artifact_path="als_model",
        )
        logger.info(
            "ALS model trained: n_users={}, n_items={}",
            user_item_matrix.shape[0],
            user_item_matrix.shape[1],
        )

        k = RECOMMENDATION_OFFLINE_EVAL_K
        truth = purchases_truth(val_int)
        cust_to_code = {str(c): i for i, c in enumerate(cust_cat.categories)}
        prod_categories = list(prod_cat.categories)
        eval_users = [
            u for u in truth["customer_id"].unique() if u in cust_to_code
        ]
        max_u = offline_max_eval_users()
        eval_users = eval_users[:max_u] if max_u > 0 else eval_users
        preds: list[dict[str, str]] = []
        for u in eval_users:
            code = cust_to_code[str(u)]
            recs = recommend_als(
                model, user_item_matrix, code, n_items=k, filter_already_liked=True
            )
            for item_code, _sc in recs:
                ic = int(item_code)
                if 0 <= ic < len(prod_categories):
                    preds.append(
                        {
                            "customer_id": str(u),
                            "product_id": str(prod_categories[ic]),
                        }
                    )
        pred_df = pd.DataFrame(preds)
        raw_eval = evaluate_prediction_df(pred_df, truth, k=k)
        offline = standard_offline_metrics(raw_eval)
        if mlflow.active_run() is not None:
            mlflow.log_params(
                log_common_reco_eval_params_mlflow(
                    DEFAULT_VAL_FRACTION,
                    k,
                    len(train_int),
                    len(val_int),
                )
            )
            mlflow.log_metrics(offline)

        return {
            "als_trained": True,
            "n_users": int(user_item_matrix.shape[0]),
            "n_items": int(user_item_matrix.shape[1]),
            "run_id": run_id,
            "model_uri": f"runs:/{run_id}/als_model",
            "offline_metrics": offline,
        }
    finally:
        try:
            if mlflow.active_run():
                mlflow.end_run()
        except Exception:
            pass
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    result = main()
    logger.info("ALS train done: {}", result)
