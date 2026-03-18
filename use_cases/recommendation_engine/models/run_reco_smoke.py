"""
Local smoke test for the recommendation engine.

Goal:
- Create/load data (via Makefile targets prior to running this script)
- Train + log MLflow models for item_similarity and ALS
- Apply in-memory by loading MLflow pyfunc models (no manual env wiring)

This is intentionally a thin orchestration wrapper so `make reco-run` exercises
the "train -> MLflow log -> MLflow load -> predict" flow end-to-end.
"""

import os

from loguru import logger

from use_cases.recommendation_engine.models.als.predict import main as als_predict
from use_cases.recommendation_engine.models.als.train import main as als_train
from use_cases.recommendation_engine.models.item_similarity.predict import (
    main as item_similarity_predict,
)
from use_cases.recommendation_engine.models.item_similarity.train import (
    main as item_similarity_train,
)
from use_cases.recommendation_engine.models.lightfm.predict import main as lightfm_predict
from use_cases.recommendation_engine.models.lightfm.train import main as lightfm_train


def _set_user_codes(n_users: int, max_users: int = 5) -> str:
    n = max(0, min(int(n_users), int(max_users)))
    return ",".join(str(i) for i in range(n))


def main(k: int = 10, max_als_users: int = 5) -> dict:
    # --- Train/log ---
    item_res = item_similarity_train()
    als_res = als_train()
    lightfm_res = lightfm_train()

    item_uri = item_res.get("model_uri")
    als_uri = als_res.get("model_uri")
    lightfm_uri = lightfm_res.get("model_uri")

    if not item_uri:
        raise RuntimeError("item_similarity_train did not return model_uri")
    if not als_uri:
        raise RuntimeError("als_train did not return model_uri")
    if not lightfm_uri:
        raise RuntimeError("lightfm_train did not return model_uri")

    # --- Apply (must load from MLflow) ---
    os.environ["ALS_USER_CODES"] = _set_user_codes(
        n_users=als_res.get("n_users", 0), max_users=max_als_users
    )

    df_item = item_similarity_predict(model_uri=item_uri, k=k)
    df_als = als_predict(model_uri=als_uri, n_items=k)
    df_lightfm = lightfm_predict(model_uri=lightfm_uri, k=k)

    logger.info(
        "Reco smoke: item_similarity_rows={}, als_rows={}, lightfm_rows={}",
        len(df_item),
        len(df_als),
        len(df_lightfm),
    )

    return {
        "item_similarity": {"model_uri": item_uri, "rows": len(df_item)},
        "als": {"model_uri": als_uri, "rows": len(df_als)},
        "lightfm": {"model_uri": lightfm_uri, "rows": len(df_lightfm)},
    }


if __name__ == "__main__":
    result = main()
    logger.info("reco smoke done: {}", result)

