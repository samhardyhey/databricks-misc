"""
Phase 3: Hybrid ranker (LightGBM LGBMRanker) combining content + collaborative features.
Requires: pip install lightgbm (or install with [reco] extra).
Logs model artefact, pyfunc (via LightGBM flavour), and metrics to MLflow when training.
"""

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import pandas as pd
from loguru import logger


def train_ranker(
    train_df: pd.DataFrame,
    feature_cols: list[str],
    group_col: str = "customer_id",
    label_col: str = "label",
    params: dict | None = None,
    eval_df: pd.DataFrame | None = None,
    eval_group_col: str | None = None,
    log_to_mlflow: bool = True,
    artifact_path: str = "ranker_model",
) -> lgb.LGBMRanker:
    """Train LGBMRanker on (customer, product, features, label). Logs model, params, and metrics to MLflow."""
    default = {"objective": "lambdarank", "metric": "ndcg", "verbosity": -1, "seed": 42}
    if params:
        default.update(params)
    X = train_df[feature_cols].fillna(0)
    y = train_df[label_col]
    groups = train_df.groupby(group_col).size().values
    model = lgb.LGBMRanker(**default)

    eval_set = None
    if eval_df is not None and eval_group_col is not None:
        X_eval = eval_df[feature_cols].fillna(0)
        y_eval = eval_df[label_col]
        eval_groups = eval_df.groupby(eval_group_col).size().values
        eval_set = [(X_eval, y_eval)]
        model.fit(X, y, group=groups, eval_set=eval_set, eval_group=[eval_groups])
    else:
        model.fit(X, y, group=groups)

    metrics = {
        "num_trees": model.n_estimators,
        "num_features": len(feature_cols),
    }
    if model.evals_result_:
        for name, hist in model.evals_result_.items():
            for m, vals in hist.items():
                if vals:
                    metrics[f"eval_{m}"] = float(vals[-1])

    if log_to_mlflow:
        from use_cases.recommendation_engine.config import apply_mlflow_config

        apply_mlflow_config()
        if mlflow.active_run() is None:
            mlflow.start_run(run_name="reco_ranker")
        mlflow.log_params(default)
        mlflow.log_metrics(metrics)
        mlflow.lightgbm.log_model(model.booster_, artifact_path)
        logger.info("Logged ranker model and metrics to MLflow")

    return model


def rank_candidates(
    model, candidate_df: pd.DataFrame, feature_cols: list[str], top_k: int = 50
) -> pd.DataFrame:
    """Score candidates and return top_k per group (e.g. per customer_id)."""
    if "customer_id" not in candidate_df.columns:
        return candidate_df.assign(
            score=model.predict(candidate_df[feature_cols].fillna(0))
        ).nlargest(top_k, "score")
    X = candidate_df[feature_cols].fillna(0)
    candidate_df = candidate_df.copy()
    candidate_df["score"] = model.predict(X)
    return (
        candidate_df.sort_values(["customer_id", "score"], ascending=[True, False])
        .groupby("customer_id", as_index=False)
        .head(top_k)
    )
