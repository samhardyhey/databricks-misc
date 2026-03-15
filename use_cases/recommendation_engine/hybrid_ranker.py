"""
Phase 3: Hybrid ranker (LightGBM LGBMRanker) combining content + collaborative features.
"""

import pandas as pd
import numpy as np
from loguru import logger

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    lgb = None


def train_ranker(
    train_df: pd.DataFrame,
    feature_cols: list[str],
    group_col: str = "customer_id",
    label_col: str = "label",
    params: dict | None = None,
) -> "lgb.Booster":
    """Train LGBMRanker on (customer, product, features, label). Groups = number of products per customer."""
    if not HAS_LIGHTGBM:
        raise ImportError("lightgbm is required: pip install lightgbm")
    default = {"objective": "lambdarank", "metric": "ndcg", "verbosity": -1, "seed": 42}
    if params:
        default.update(params)
    X = train_df[feature_cols].fillna(0)
    y = train_df[label_col]
    groups = train_df.groupby(group_col).size().values
    model = lgb.LGBMRanker(**default)
    model.fit(X, y, group=groups)
    return model


def rank_candidates(
    model, candidate_df: pd.DataFrame, feature_cols: list[str], top_k: int = 50
) -> pd.DataFrame:
    """Score candidates and return top_k per group (e.g. per customer_id)."""
    if "customer_id" not in candidate_df.columns:
        return candidate_df.assign(score=model.predict(candidate_df[feature_cols].fillna(0))).nlargest(top_k, "score")
    X = candidate_df[feature_cols].fillna(0)
    candidate_df = candidate_df.copy()
    candidate_df["score"] = model.predict(X)
    return (
        candidate_df.sort_values(["customer_id", "score"], ascending=[True, False])
        .groupby("customer_id", as_index=False)
        .head(top_k)
    )
