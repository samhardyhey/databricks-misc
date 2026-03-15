"""
Reco metrics: Precision@K, Recall@K, NDCG.
"""

import numpy as np
import pandas as pd
from loguru import logger


def precision_at_k(relevant: set, recommended: list, k: int) -> float:
    """Precision@k = |relevant ∩ recommended[:k]| / k."""
    rec_k = set(recommended[:k]) if isinstance(recommended, (list, np.ndarray)) else set(list(recommended)[:k])
    return len(relevant & rec_k) / k if k > 0 else 0.0


def recall_at_k(relevant: set, recommended: list, k: int) -> float:
    """Recall@k = |relevant ∩ recommended[:k]| / |relevant|."""
    if not relevant:
        return 0.0
    rec_k = set(recommended[:k]) if isinstance(recommended, (list, np.ndarray)) else set(list(recommended)[:k])
    return len(relevant & rec_k) / len(relevant)


def dcg_at_k(relevant: set, recommended: list, k: int) -> float:
    """DCG@k (binary relevance)."""
    rec = list(recommended)[:k] if hasattr(recommended, "__iter__") and not isinstance(recommended, set) else recommended[:k]
    dcg = 0.0
    for i, item in enumerate(rec):
        if item in relevant:
            dcg += 1.0 / np.log2(i + 2)
    return dcg


def ndcg_at_k(relevant: set, recommended: list, k: int) -> float:
    """NDCG@k = DCG@k / IDCG@k (binary relevance)."""
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    if idcg <= 0:
        return 0.0
    return dcg_at_k(relevant, recommended, k) / idcg


def evaluate_recommendations(
    pred_df: pd.DataFrame,
    truth_df: pd.DataFrame,
    user_col: str = "customer_id",
    item_col: str = "product_id",
    k: int = 10,
) -> dict[str, float]:
    """
    pred_df: (user_col, item_col, [rank]); recommended items per user.
    truth_df: (user_col, item_col); relevant (e.g. purchased) items per user.
    """
    truth_by_user = truth_df.groupby(user_col)[item_col].apply(set).to_dict()
    pred_by_user = pred_df.groupby(user_col)[item_col].apply(list).to_dict()
    users = set(truth_by_user) & set(pred_by_user)
    if not users:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "ndcg_at_k": 0.0}
    p, r, n = [], [], []
    for u in users:
        rel = truth_by_user[u]
        rec = pred_by_user[u]
        p.append(precision_at_k(rel, rec, k))
        r.append(recall_at_k(rel, rec, k))
        n.append(ndcg_at_k(rel, rec, k))
    return {
        "precision_at_k": float(np.mean(p)),
        "recall_at_k": float(np.mean(r)),
        "ndcg_at_k": float(np.mean(n)),
    }
