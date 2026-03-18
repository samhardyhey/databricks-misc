"""
Core LightFM recommender utilities.

Implements an implicit-feedback matrix factorization model using the LightFM
library (https://making.lyst.com/lightfm/docs/). This model complements
item-similarity and ALS by supporting hybrid user/item-feature models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import joblib
import mlflow.pyfunc
import numpy as np
import pandas as pd
from lightfm import LightFM
from lightfm.data import Dataset
from loguru import logger


@dataclass
class LightFMArtifacts:
    model: LightFM
    dataset: Dataset
    user_id_map: dict[str, int]
    item_id_map: dict[str, int]
    user_feature_map: Optional[dict[str, int]] = None
    item_feature_map: Optional[dict[str, int]] = None


class LightFMRecoWrapper(mlflow.pyfunc.PythonModel):
    """
    MLflow pyfunc wrapper for LightFM recommendations.

    Input (model_input DataFrame):
      - customer_id (str)
      - optional k (int) (falls back to self.k)

    Output DataFrame:
      - customer_id
      - product_id
      - score
      - rank
    """

    def __init__(self, k: int = 10) -> None:
        self.k = int(k)

    def load_context(self, context) -> None:
        payload = joblib.load(context.artifacts["lightfm_artifacts"])
        self.model = payload["model"]
        self.user_id_map = payload["user_id_map"]
        self.item_id_map = payload["item_id_map"]
        self.n_items = int(payload["n_items"])

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        if "customer_id" not in model_input.columns:
            raise ValueError("model_input must include column `customer_id`")

        k = self.k
        if "k" in model_input.columns and len(model_input) > 0:
            k = int(model_input["k"].iloc[0])

        inv_item_map = {v: k for k, v in self.item_id_map.items()}

        user_ids = model_input["customer_id"].astype(str).tolist()
        rows: list[dict] = []
        for uid in user_ids:
            if uid not in self.user_id_map:
                continue
            internal_u = int(self.user_id_map[uid])
            scores = self.model.predict(
                internal_u, np.arange(self.n_items, dtype=np.int32)
            )
            topk = np.argsort(-scores)[:k]
            for rank, item_idx in enumerate(topk, start=1):
                rows.append(
                    {
                        "customer_id": uid,
                        "product_id": inv_item_map[int(item_idx)],
                        "score": float(scores[int(item_idx)]),
                        "rank": rank,
                    }
                )
        return pd.DataFrame(rows)


def build_lightfm_dataset(
    interactions: pd.DataFrame,
    user_col: str = "customer_id",
    item_col: str = "product_id",
    rating_col: Optional[str] = None,
    user_features: Optional[pd.DataFrame] = None,
    item_features: Optional[pd.DataFrame] = None,
) -> tuple[Dataset, dict[str, int], dict[str, int]]:
    """
    Build a LightFM Dataset from interactions (and optional user/item features).

    Interactions: rows with at least user_col and item_col; rating_col is optional
    (implicit feedback => 1.0 when missing).
    """
    users = interactions[user_col].astype(str).unique().tolist()
    items = interactions[item_col].astype(str).unique().tolist()

    ds = Dataset()
    ds.fit(
        users=users,
        items=items,
    )

    user_id_map, _, item_id_map, _ = ds.mapping()

    logger.info(
        "LightFM dataset built: n_users={}, n_items={}",
        len(user_id_map),
        len(item_id_map),
    )
    return ds, user_id_map, item_id_map


def build_interaction_matrix_lightfm(
    interactions: pd.DataFrame,
    dataset: Dataset,
    user_col: str = "customer_id",
    item_col: str = "product_id",
    rating_col: Optional[str] = None,
):
    """
    Build a sparse interaction matrix suitable for LightFM.fit.
    """
    rows = interactions[user_col].astype(str).tolist()
    cols = interactions[item_col].astype(str).tolist()
    if rating_col is not None and rating_col in interactions.columns:
        ratings = interactions[rating_col].astype(float).tolist()
    else:
        ratings = [1.0] * len(interactions)

    mat = dataset.build_interactions(zip(rows, cols, ratings))[0]
    return mat


def train_lightfm(
    interactions: pd.DataFrame,
    no_components: int = 30,
    loss: str = "warp",
    epochs: int = 20,
    num_threads: int = 4,
    user_col: str = "customer_id",
    item_col: str = "product_id",
    rating_col: Optional[str] = None,
) -> LightFMArtifacts:
    """
    Train a LightFM model on implicit feedback interactions.
    """
    ds, user_map, item_map = build_lightfm_dataset(
        interactions,
        user_col=user_col,
        item_col=item_col,
        rating_col=rating_col,
    )
    mat = build_interaction_matrix_lightfm(
        interactions,
        ds,
        user_col=user_col,
        item_col=item_col,
        rating_col=rating_col,
    )

    model = LightFM(no_components=no_components, loss=loss)
    logger.info(
        "Training LightFM: components={}, loss={}, epochs={}, num_threads={}",
        no_components,
        loss,
        epochs,
        num_threads,
    )
    model.fit(mat, epochs=epochs, num_threads=num_threads)
    return LightFMArtifacts(
        model=model,
        dataset=ds,
        user_id_map=user_map,
        item_id_map=item_map,
    )


def recommend_for_users(
    artifacts: LightFMArtifacts,
    user_ids: list[str],
    k: int = 10,
) -> pd.DataFrame:
    """
    Recommend top-k items for each user in user_ids.
    """
    model = artifacts.model
    artifacts.dataset
    user_map = artifacts.user_id_map
    item_map = artifacts.item_id_map
    inv_item_map = {v: k for k, v in item_map.items()}

    n_items = len(item_map)
    rows = []
    for uid in user_ids:
        if uid not in user_map:
            continue
        internal_u = user_map[uid]
        # Score all items; for large catalogs we would want candidates only
        scores = model.predict(internal_u, np.arange(n_items, dtype=np.int32))
        topk = np.argsort(-scores)[:k]
        for rank, item_idx in enumerate(topk, start=1):
            rows.append(
                {
                    "customer_id": uid,
                    "product_id": inv_item_map[item_idx],
                    "score": float(scores[item_idx]),
                    "rank": rank,
                }
            )
    return pd.DataFrame(rows)
