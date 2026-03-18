"""
Core item-to-item similarity utilities (sklearn NearestNeighbors, cosine).

All model-specific code for item_similarity lives under models/item_similarity/.
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

import mlflow.pyfunc


def train_item_similarity(
    product_features: pd.DataFrame, n_neighbors: int = 50, metric: str = "cosine"
):
    """Fit NearestNeighbors on product feature matrix. product_features: index=product_id, columns=numeric."""
    X = product_features.values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(np.nan_to_num(X, nan=0.0))
    nn = NearestNeighbors(
        n_neighbors=min(n_neighbors + 1, len(product_features)),
        metric=metric,
        algorithm="brute",
    )
    nn.fit(X_scaled)
    return nn, scaler, product_features.index.tolist()


def recommend_similar_items(
    nn,
    scaler,
    product_ids: list,
    product_features: pd.DataFrame,
    product_id: str,
    k: int = 10,
) -> list[tuple[str, float]]:
    """Return top-k similar product (id, distance) for a given product_id."""
    if product_id not in product_ids:
        return []
    idx = product_ids.index(product_id)
    X = product_features.values
    X_scaled = scaler.transform(np.nan_to_num(X, nan=0.0))
    distances, indices = nn.kneighbors(
        X_scaled[idx : idx + 1], n_neighbors=min(k + 1, len(product_ids))
    )
    out = []
    for dist, ind in zip(distances[0], indices[0]):
        if ind != idx:
            out.append((product_ids[ind], float(dist)))
    return out[:k]


def recommend_similar_items_batch(
    nn,
    scaler,
    product_ids: list,
    product_features: pd.DataFrame,
    query_product_ids: list[str],
    k: int = 10,
) -> dict[str, list[tuple[str, float]]]:
    """Batch version: for each query product return top-k similar."""
    return {
        pid: recommend_similar_items(
            nn, scaler, product_ids, product_features, pid, k=k
        )
        for pid in query_product_ids
    }


class ItemSimilarityRecoWrapper(mlflow.pyfunc.PythonModel):
    """
    MLflow pyfunc wrapper for item_similarity.

    Expects model_input with:
      - product_id (str)
      - optional k (int) per row (falls back to self.k)
    Returns a DataFrame with:
      - product_id
      - similar_product_id
      - similarity_score
      - rank
    """

    def __init__(self, k: int = 10) -> None:
        self.k = k

    def load_context(self, context) -> None:
        payload_path = context.artifacts["item_similarity"]
        payload = joblib.load(payload_path)
        self.nn = payload["nn"]
        self.scaler = payload["scaler"]
        self.product_features = payload["product_features"]
        self.product_ids = payload["product_ids"]

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        if "product_id" not in model_input.columns:
            raise ValueError("model_input must include column `product_id`")

        k = self.k
        if "k" in model_input.columns and len(model_input) > 0:
            # k is expected to be constant across rows for smoke testing.
            k = int(model_input["k"].iloc[0])

        query_product_ids = model_input["product_id"].tolist()
        rows: list[dict] = []
        for pid in query_product_ids:
            sim_list = recommend_similar_items(
                self.nn, self.scaler, self.product_ids, self.product_features, pid, k=k
            )
            for rank, (sim_pid, score) in enumerate(sim_list, start=1):
                rows.append(
                    {
                        "product_id": pid,
                        "similar_product_id": sim_pid,
                        "similarity_score": float(score),
                        "rank": rank,
                    }
                )
        return pd.DataFrame(rows)
