"""
Reco run config: data source (local CSV vs Unity Catalog), paths, and MLflow.
Switch via RECO_DATA_SOURCE and environment; same code path for train/eval.
MLflow: local -> ./mlruns (or under local_data_dir); Databricks -> workspace + Unity Catalog registry.
"""

import os
from pathlib import Path
from typing import Literal

from use_cases.env_utils import is_running_on_databricks

# Defaults (overridable by env)
_DEFAULT_LOCAL_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "local"
_DEFAULT_CATALOG_SCHEMA = "workspace.healthcare_medallion"

DataSource = Literal["local", "catalog", "auto"]


def get_data_source() -> Literal["local", "catalog"]:
    """
    Resolved data source: 'local' (CSV) or 'catalog' (Unity Catalog).
    RECO_DATA_SOURCE: 'local' | 'catalog' | 'auto'.
    - 'auto': use 'catalog' on Databricks (DATABRICKS_RUNTIME_VERSION set), else 'local'.
    - Explicit 'local'/'catalog' override (e.g. Databricks Connect + catalog).
    """
    raw = os.environ.get("RECO_DATA_SOURCE", "auto").strip().lower()
    if raw == "catalog":
        return "catalog"
    if raw == "local":
        return "local"
    # auto
    return "catalog" if is_running_on_databricks() else "local"


def get_local_data_dir() -> Path:
    """Directory for local CSVs (e.g. data/local). Override with LOCAL_DATA_PATH."""
    p = os.environ.get("LOCAL_DATA_PATH", str(_DEFAULT_LOCAL_DATA_DIR))
    return Path(p).resolve()


def get_duckdb_path() -> Path | None:
    """
    Path to local DuckDB medallion file when data_source is local.
    From DBT_DUCKDB_PATH (default data/local/medallion.duckdb relative to repo).
    Returns None if the file does not exist.
    """
    raw = os.environ.get("DBT_DUCKDB_PATH")
    if raw:
        p = Path(raw).resolve()
    else:
        # Default: data/local/medallion.duckdb relative to repo (config is under use_cases/recommendation_engine)
        repo = Path(__file__).resolve().parents[2]
        p = (repo / "data" / "local" / "medallion.duckdb").resolve()
    return p if p.is_file() else None


def get_duckdb_medallion_schema() -> str:
    """
    Base schema name for DuckDB medallion (dbt builds e.g. {base}_silver, {base}_gold).
    Override with DBT_DUCKDB_MEDALLION_SCHEMA. Default matches dbt duckdb profile local.
    """
    return os.environ.get(
        "DBT_DUCKDB_MEDALLION_SCHEMA", "healthcare_medallion_local"
    ).strip()


def get_local_data_source() -> Literal["duckdb", "csv"]:
    """
    When data_source is 'local', prefer 'duckdb' (DuckDB medallion) if DBT_DUCKDB_PATH
    exists and is a file; otherwise 'csv' (data/local CSVs). Loaders fall back to CSV
    if DuckDB is chosen but tables are missing.
    """
    if get_duckdb_path() is not None:
        return "duckdb"
    return "csv"


def get_catalog_schema() -> str:
    """Unity Catalog schema for reco tables (e.g. workspace.healthcare_medallion). Override with RECO_CATALOG_SCHEMA."""
    return os.environ.get("RECO_CATALOG_SCHEMA", _DEFAULT_CATALOG_SCHEMA)


def get_mlflow_tracking_uri() -> str | None:
    """
    MLflow tracking URI: local path when not on Databricks, None on Databricks (use workspace default).
    Override with MLFLOW_TRACKING_URI.
    """
    if os.environ.get("MLFLOW_TRACKING_URI"):
        return os.environ["MLFLOW_TRACKING_URI"]
    if is_running_on_databricks():
        return None
    return str(get_local_data_dir() / "mlruns")


def get_mlflow_registry_uri() -> str | None:
    """
    MLflow registry URI: None when local, 'databricks-uc' on Databricks for Unity Catalog.
    Override with MLFLOW_REGISTRY_URI.
    """
    if os.environ.get("MLFLOW_REGISTRY_URI"):
        return os.environ["MLFLOW_REGISTRY_URI"]
    if is_running_on_databricks():
        return "databricks-uc"
    return None


def apply_mlflow_config(config: dict | None = None) -> None:
    """
    Set MLflow tracking and registry URIs from config (local vs Databricks).
    Call before logging models so runs go to local mlruns or Databricks + Unity Catalog.
    config: from get_config() if None (currently only env / on_databricks are used for URIs).
    """
    import mlflow

    tracking = get_mlflow_tracking_uri()
    if tracking is not None:
        mlflow.set_tracking_uri(tracking)
    registry = get_mlflow_registry_uri()
    if registry is not None:
        mlflow.set_registry_uri(registry)


def get_config() -> dict:
    """
    Single config dict for the reco pipeline.
    - data_source: 'local' | 'catalog'
    - local_data_dir: Path (used when data_source == 'local', CSV fallback)
    - local_data_source: 'duckdb' | 'csv' (when data_source == 'local': prefer DuckDB medallion)
    - duckdb_path: Path | None (when local and DuckDB file exists)
    - duckdb_medallion_schema: str (base schema for DuckDB, e.g. healthcare_medallion_local)
    - catalog_schema: str (used when data_source == 'catalog')
    - on_databricks: bool (is_running_on_databricks())
    - mlflow_tracking_uri: str | None
    - mlflow_registry_uri: str | None
    """
    data_source = get_data_source()
    duckdb_path = get_duckdb_path()
    return {
        "data_source": data_source,
        "local_data_dir": get_local_data_dir(),
        "local_data_source": get_local_data_source(),
        "duckdb_path": duckdb_path,
        "duckdb_medallion_schema": get_duckdb_medallion_schema(),
        "catalog_schema": get_catalog_schema(),
        "on_databricks": is_running_on_databricks(),
        "mlflow_tracking_uri": get_mlflow_tracking_uri(),
        "mlflow_registry_uri": get_mlflow_registry_uri(),
    }
