"""
Core item-to-item similarity utilities (sklearn NearestNeighbors, cosine).

Moved here from use_cases/recommendation_engine/item_similarity.py so that
all model-specific code for item_similarity lives under models/item_similarity/.
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


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

