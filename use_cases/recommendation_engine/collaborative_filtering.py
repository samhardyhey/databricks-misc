"""
Phase 2: Collaborative filtering (implicit ALS).
Requires: pip install implicit (or install with [reco] extra).
"""

import numpy as np
from implicit.als import AlternatingLeastSquares
from loguru import logger
from scipy.sparse import csr_matrix


def train_als(
    user_ids: np.ndarray,
    item_ids: np.ndarray,
    weights: np.ndarray,
    factors: int = 64,
    iterations: int = 15,
    regularization: float = 0.01,
):
    """Build user-item matrix and fit ALS. user_ids/item_ids are 0-based integer codes. Returns (model, csr_matrix)."""
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
        filter_already_liked=filter_already_liked,
    )
    return list(zip(item_ids, scores.astype(float)))
