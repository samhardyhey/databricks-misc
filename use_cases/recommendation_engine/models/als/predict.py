"""
Batch apply ALS collaborative filtering model for a set of users.

Uses the ALSRecoWrapper pyfunc logged by train_als. Expects MLflow model URI
(env ALS_MODEL_URI, default models:/RECO_als/Production). Requires [reco] extra. Run: make reco-install.
"""

import os
from typing import Optional

import mlflow
import pandas as pd
from loguru import logger
from mlflow.exceptions import MlflowException

from use_cases.recommendation_engine.config import apply_mlflow_config, get_config


def _load_als_model(model_uri: Optional[str] = None):
    """
    Load ALS model from MLflow. Locally use a runs:/ or file:// URI (set ALS_MODEL_URI);
    on Databricks jobs can set ALS_MODEL_URI to a registry URI (e.g. models:/RECO_als/Production).
    Returns None if the URI is not set or load fails.
    """
    uri = model_uri or os.environ.get("ALS_MODEL_URI")
    if not uri:
        logger.info(
            "ALS predict skipped: ALS_MODEL_URI is not set; set it to a model URI "
            "(e.g. runs:/<run_id>/model locally or models:/RECO_als/Production on Databricks)."
        )
        return None
    logger.info("Loading ALS model from {}", uri)
    try:
        return mlflow.pyfunc.load_model(uri)
    except MlflowException as e:
        logger.info(
            "ALS predict skipped: could not load model from '{}': {}", uri, e
        )
        return None


def main(model_uri: Optional[str] = None, n_items: int = 10) -> pd.DataFrame:
    cfg = get_config()
    logger.info(
        "ALS predict: data_source={}, on_databricks={}",
        cfg["data_source"],
        cfg["on_databricks"],
    )

    apply_mlflow_config(cfg)

    model = _load_als_model(model_uri=model_uri)
    if model is None:
        logger.info("ALS predict: no model available; returning empty DataFrame.")
        return pd.DataFrame()

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

