"""
Core ALS collaborative filtering utilities.

Moved here from use_cases/recommendation_engine/collaborative_filtering.py so that
all ALS-specific code lives under models/als/.
"""

import tempfile
from pathlib import Path

import joblib
import mlflow
import mlflow.pyfunc
import numpy as np
import pandas as pd
from implicit.als import AlternatingLeastSquares  # type: ignore[import-untyped]
from loguru import logger
from scipy.sparse import csr_matrix


class ALSRecoWrapper(mlflow.pyfunc.PythonModel):
    """MLflow pyfunc wrapper: predict expects DataFrame with user_code (and optional n_items); returns recommendations."""

    def load_context(self, context):
        path = context.artifacts["als_model"]
        data = joblib.load(path)
        self.model = data["model"]
        self.user_item_matrix = data["user_item_matrix"]

    def predict(
        self, context, model_input: pd.DataFrame, params: dict | None = None
    ) -> pd.DataFrame:
        n_items = 10
        if params and "n_items" in params:
            n_items = int(params["n_items"])
        if "user_code" not in model_input.columns:
            raise ValueError("model_input must have column user_code")
        user_codes = model_input["user_code"].astype(int).values
        out = []
        for u in user_codes:
            user_row = self.user_item_matrix[u]
            item_ids, scores = self.model.recommend(
                userid=u,
                user_items=user_row,
                N=n_items,
                filter_already_liked_items=True,
            )
            out.append(
                {
                    "user_code": u,
                    "recommended_item_codes": item_ids.tolist(),
                    "recommended_scores": scores.astype(float).tolist(),
                }
            )
        return pd.DataFrame(out)


def train_als(
    user_ids: np.ndarray,
    item_ids: np.ndarray,
    weights: np.ndarray,
    factors: int = 64,
    iterations: int = 15,
    regularization: float = 0.01,
    log_to_mlflow: bool = True,
    artifact_path: str = "als_model",
):
    """Build user-item matrix and fit ALS. Logs model, pyfunc, and metrics to MLflow. Returns (model, csr_matrix)."""
    n_users = int(user_ids.max()) + 1
    n_items = int(item_ids.max()) + 1
    M = csr_matrix((weights, (user_ids, item_ids)), shape=(n_users, n_items))
    model = AlternatingLeastSquares(
        factors=factors,
        iterations=iterations,
        regularization=regularization,
        random_state=42,
    )
    model.fit(M)

    metrics = {
        "n_users": n_users,
        "n_items": n_items,
        "n_factors": factors,
        "n_nonzero": int(M.nnz),
        "iterations": iterations,
    }

    if log_to_mlflow:
        # Expect caller to have already called apply_mlflow_config() and/or started a run.
        # If no run is active, start one so the model is still logged.
        if mlflow.active_run() is None:
            mlflow.start_run(run_name="reco_als")
        with tempfile.TemporaryDirectory() as tmp:
            art_path = Path(tmp) / "als_data.joblib"
            joblib.dump({"model": model, "user_item_matrix": M}, art_path)
            mlflow.log_params(
                {
                    "factors": factors,
                    "iterations": iterations,
                    "regularization": regularization,
                }
            )
            mlflow.log_metrics(metrics)
            mlflow.pyfunc.log_model(
                artifact_path=artifact_path,
                python_model=ALSRecoWrapper(),
                artifacts={"als_model": str(art_path)},
                registered_model_name=None,
            )
        logger.info("Logged ALS model and metrics to MLflow")

    return model, M


def recommend_als(
    model,
    user_item_matrix,
    user_code: int,
    n_items: int = 10,
    filter_already_liked: bool = True,
) -> list[tuple[int, float]]:
    """Recommend top-n items for a user (by internal code). Returns list of (item_code, score)."""
    user_row = user_item_matrix[user_code]
    item_ids, scores = model.recommend(
        userid=user_code,
        user_items=user_row,
        N=n_items,
        filter_already_liked_items=filter_already_liked,
    )
    return list(zip(item_ids, scores.astype(float)))
