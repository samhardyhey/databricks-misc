"""
Shared MLflow config: backend and artifact location by environment (local vs Databricks).

Single source of truth for MLflow tracking URI and artifact root. Used by reco/inventory
configs and by the local MLflow UI (make mlflow-ui). Override with MLFLOW_TRACKING_URI;
local default is SQLite in data/local (LOCAL_DATA_PATH).
"""

import os
from pathlib import Path

from use_cases.env_utils import is_running_on_databricks

# Repo root: use_cases/mlflow/config.py -> parents[2] = repo
_DEFAULT_LOCAL_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "local"


def get_local_data_dir() -> Path:
    """
    Directory for local MLflow DB and artifacts (e.g. data/local).
    Override with LOCAL_DATA_PATH. Same convention as reco/inventory data paths.
    """
    p = os.environ.get("LOCAL_DATA_PATH", str(_DEFAULT_LOCAL_DATA_DIR))
    return Path(p).resolve()


def get_mlflow_tracking_uri() -> str | None:
    """
    MLflow tracking URI: switches on environment.
    - MLFLOW_TRACKING_URI set: use it.
    - Databricks: None (use workspace default).
    - Local: sqlite:///<local_data_dir>/mlflow.db.
    """
    if os.environ.get("MLFLOW_TRACKING_URI"):
        return os.environ["MLFLOW_TRACKING_URI"]
    if is_running_on_databricks():
        return None
    db_path = (get_local_data_dir() / "mlflow.db").resolve()
    return f"sqlite:///{db_path}"


def get_mlflow_artifact_root() -> str | None:
    """
    Default artifact root when using local SQLite backend.
    None on Databricks or when tracking URI is not local SQLite.
    Same as make mlflow-ui --default-artifact-root so client and UI share artifacts.
    """
    if is_running_on_databricks():
        return None
    tracking = get_mlflow_tracking_uri()
    if not tracking or not tracking.startswith("sqlite:"):
        return None
    return f"file://{(get_local_data_dir() / 'mlruns').resolve()}"


def get_mlflow_registry_uri() -> str | None:
    """
    MLflow registry URI: None when local; 'databricks-uc' on Databricks for Unity Catalog.
    Override with MLFLOW_REGISTRY_URI.
    """
    if os.environ.get("MLFLOW_REGISTRY_URI"):
        return os.environ["MLFLOW_REGISTRY_URI"]
    if is_running_on_databricks():
        return "databricks-uc"
    return None


def apply_mlflow_config() -> None:
    """
    Set MLflow tracking and registry URIs from environment (local vs Databricks).
    Call before set_experiment/start_run so runs go to local SQLite or Databricks + UC.
    Used by both recommendation_engine and inventory_optimization for consistent logging.
    """
    import mlflow

    tracking = get_mlflow_tracking_uri()
    if tracking is not None:
        mlflow.set_tracking_uri(tracking)
    registry = get_mlflow_registry_uri()
    if registry is not None:
        mlflow.set_registry_uri(registry)


def ensure_experiment_artifact_root(experiment_name: str) -> None:
    """
    If tracking is local SQLite, ensure the experiment exists with artifact_location
    in data/local/mlruns so artifacts appear in the MLflow UI. No-op on Databricks or
    if experiment already exists.
    """
    artifact_root = get_mlflow_artifact_root()
    if artifact_root is None:
        return
    from mlflow import MlflowClient

    client = MlflowClient()
    exp = client.get_experiment_by_name(experiment_name)
    if exp is None:
        client.create_experiment(experiment_name, artifact_location=artifact_root)
