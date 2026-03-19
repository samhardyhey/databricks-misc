"""
Train a LightGBM ranker for recommendation_engine.
"""

import mlflow
import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import (
    apply_mlflow_config,
    ensure_experiment_artifact_root,
    get_config,
)
from use_cases.recommendation_engine.models.data_loading import load_reco_data
from use_cases.recommendation_engine.models.feature_engineering import (
    add_negative_samples,
    build_ranker_feature_frame,
)
from use_cases.recommendation_engine.models.ranker.core import (
    rank_candidates,
    train_ranker,
)
from use_cases.recommendation_engine.models.reco_split_eval import (
    DEFAULT_VAL_FRACTION,
    RECOMMENDATION_OFFLINE_EVAL_K,
    evaluate_prediction_df,
    log_common_reco_eval_params_mlflow,
    offline_max_eval_users,
    purchases_truth,
    standard_offline_metrics,
    temporal_train_val_split,
)
from use_cases.recommendation_engine.pipelines.build_training_base import (
    _compute_training_base,
)
from utils.mlflow.registry import set_latest_version_alias


def _prepare_training_base_df(training_base: pd.DataFrame) -> pd.DataFrame:
    df = training_base.copy()
    if "label" not in df.columns:
        df["label"] = 1
    return df


def main() -> dict:
    cfg = get_config()
    logger.info(
        "Ranker train: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    spark = None
    if cfg["data_source"] == "catalog" and cfg["on_databricks"]:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("RecoRankerTrain").getOrCreate()

    try:
        data = load_reco_data(config=cfg, spark=spark)
        interactions = data.get("interactions")
        products = data.get("products")
        if products is None or interactions is None or interactions.empty:
            raise RuntimeError(
                "Ranker training requires interactions + products for temporal split. "
                "Local: make reco-data. Catalog: silver_reco_interactions + silver_products."
            )

        products = products.copy()
        products["product_id"] = products["product_id"].astype(str)

        train_int, val_int = temporal_train_val_split(
            interactions, val_fraction=DEFAULT_VAL_FRACTION
        )
        tb_raw = _compute_training_base(train_int)
        tb_raw["customer_id"] = tb_raw["customer_id"].astype(str)
        tb_raw["product_id"] = tb_raw["product_id"].astype(str)
        training_base = _prepare_training_base_df(tb_raw)

        sampled = add_negative_samples(training_base, products, n_neg_per_pos=2)
        train_df, feature_cols = build_ranker_feature_frame(sampled, products)

        apply_mlflow_config(cfg)
        experiment = "recommendation_engine-ranker"
        ensure_experiment_artifact_root(experiment)
        mlflow.set_experiment(experiment)

        k = RECOMMENDATION_OFFLINE_EVAL_K
        offline: dict[str, float] = {}
        with mlflow.start_run(run_name="ranker_train") as run:
            model = train_ranker(
                train_df=train_df,
                feature_cols=feature_cols,
                group_col="customer_id",
                label_col="label",
                log_to_mlflow=False,
            )
            truth = purchases_truth(val_int)
            pos_users_train = training_base.loc[
                training_base["label"] == 1, "customer_id"
            ].unique()
            eval_users = [
                u for u in truth["customer_id"].unique() if u in set(pos_users_train)
            ]
            max_u = offline_max_eval_users()
            if max_u > 0 and len(eval_users) > max_u:
                eval_users = eval_users[:max_u]
            pids = products["product_id"].unique()
            if eval_users:
                rows = []
                for u in eval_users:
                    for pid in pids:
                        rows.append({"customer_id": str(u), "product_id": str(pid)})
                cand = pd.DataFrame(rows)
                cand = cand.merge(
                    training_base,
                    on=["customer_id", "product_id"],
                    how="left",
                )
                if "label" in cand.columns:
                    cand = cand.drop(columns=["label"])
                cand["label"] = 0
                num_fill = [
                    c
                    for c in cand.columns
                    if c
                    not in ("customer_id", "product_id", "last_interaction_timestamp")
                ]
                if num_fill:
                    cand[num_fill] = cand[num_fill].fillna(0)
                scored, _ = build_ranker_feature_frame(cand, products)
                for c in feature_cols:
                    if c not in scored.columns:
                        scored[c] = 0
                pred_wide = rank_candidates(model, scored, feature_cols, top_k=k)
                pred_df = pred_wide[["customer_id", "product_id"]].copy()
                raw_ev = evaluate_prediction_df(pred_df, truth, k=k)
                offline = standard_offline_metrics(raw_ev)

            mlflow.log_params(
                {
                    "n_features": len(feature_cols),
                    "n_rows": len(train_df),
                    **log_common_reco_eval_params_mlflow(
                        DEFAULT_VAL_FRACTION,
                        k,
                        len(train_int),
                        len(val_int),
                    ),
                }
            )
            mlflow.log_metrics(
                offline
                or standard_offline_metrics(
                    {"precision_at_k": 0.0, "recall_at_k": 0.0, "ndcg_at_k": 0.0}
                )
            )
            mlflow.lightgbm.log_model(
                model.booster_,
                artifact_path="ranker_model",
                registered_model_name="recommendation_engine-ranker",
            )
            set_latest_version_alias("recommendation_engine-ranker", alias="Champion")

        model_uri = f"runs:/{run.info.run_id}/ranker_model"
        logger.info("Ranker trained; model_uri={}", model_uri)
        return {
            "model_uri": model_uri,
            "n_rows": len(train_df),
            "n_features": len(feature_cols),
            "offline_metrics": offline,
        }
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    result = main()
    logger.info("Ranker train done: {}", result)
