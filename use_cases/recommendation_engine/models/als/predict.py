"""
Batch apply ALS collaborative filtering model for a set of users.

Current behaviour:
- Uses the ALSRecoWrapper pyfunc logged by collaborative_filtering.train_als.
- Expects a MLflow model URI (env ALS_MODEL_URI, default models:/RECO_als/Production).
- Returns a DataFrame of recommendations per user; on Databricks, this can be
  extended to write to a gold table.
"""

import os
from typing import Optional

import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import apply_mlflow_config, get_config


def _load_als_model(model_uri: Optional[str] = None):
    try:
        import mlflow
    except ImportError:
        raise RuntimeError("mlflow is required to load the ALS model.")

    uri = model_uri or os.environ.get("ALS_MODEL_URI", "models:/RECO_als/Production")
    logger.info("Loading ALS model from {}", uri)
    return mlflow.pyfunc.load_model(uri)


def main(model_uri: Optional[str] = None, n_items: int = 10) -> pd.DataFrame:
    cfg = get_config()
    logger.info(
        "ALS predict: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    try:
        import mlflow
    except ImportError:
        mlflow = None  # type: ignore[assignment]

    if mlflow is not None:
        apply_mlflow_config(cfg)

    model = _load_als_model(model_uri=model_uri)

    # For now we expect a simple CSV of user_codes to score (local) or
    # future extension to read from a medallion table when on Databricks.
    user_codes_str = os.environ.get("ALS_USER_CODES", "")
    if not user_codes_str:
        logger.warning("ALS_USER_CODES not set; nothing to score.")
        return pd.DataFrame()
    user_codes = [int(x) for x in user_codes_str.split(",") if x.strip()]
    df_in = pd.DataFrame({"user_code": user_codes})
    logger.info("Scoring ALS for {} users", len(df_in))

    out = model.predict(df_in, params={"n_items": n_items})
    return out


if __name__ == "__main__":
    df = main()
    logger.info("Generated ALS recommendations for {} users", len(df))

