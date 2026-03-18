"""
Reco run config: data source (local CSV vs Unity Catalog), paths, and MLflow.
Switch via RECO_DATA_SOURCE and environment; same code path for train/eval.
MLflow: see utils.mlflow.config (local SQLite vs Databricks workspace).
"""

import os
from pathlib import Path
from typing import Literal

from utils.use_case_utils import (
    get_catalog_schema as _get_catalog_schema,
    get_duckdb_medallion_schema as _get_duckdb_medallion_schema,
    get_duckdb_path as _get_duckdb_path,
    get_local_data_dir as _get_local_data_dir,
    get_local_data_source as _get_local_data_source,
    resolve_data_source,
)
from utils.env_utils import is_running_on_databricks
from utils.use_case_utils import (
    apply_mlflow_config as _apply_mlflow_config,
    ensure_experiment_artifact_root,
    get_mlflow_registry_uri as _get_mlflow_registry_uri,
    get_mlflow_tracking_uri,
)

DataSource = Literal["local", "catalog", "auto"]


def get_data_source() -> Literal["local", "catalog"]:
    """
    Resolved data source: 'local' (CSV) or 'catalog' (Unity Catalog).
    RECO_DATA_SOURCE: 'local' | 'catalog' | 'auto'.
    - 'auto': use 'catalog' on Databricks (DATABRICKS_RUNTIME_VERSION set), else 'local'.
    - Explicit 'local'/'catalog' override (e.g. Databricks Connect + catalog).
    """
    return resolve_data_source(env_var_name="RECO_DATA_SOURCE")


def get_local_data_dir() -> Path:
    """Directory for local CSVs (e.g. data/local). Override with LOCAL_DATA_PATH."""
    return _get_local_data_dir(env_var_name="LOCAL_DATA_PATH")


def get_duckdb_path() -> Path | None:
    """
    Path to local DuckDB medallion file when data_source is local.
    From DBT_DUCKDB_PATH (default data/local/medallion.duckdb relative to repo).
    Returns None if the file does not exist.
    """
    return _get_duckdb_path(env_var_name="DBT_DUCKDB_PATH")


def get_duckdb_medallion_schema() -> str:
    """
    Base schema name for DuckDB medallion (dbt builds e.g. {base}_silver, {base}_gold).
    Override with DBT_DUCKDB_MEDALLION_SCHEMA. Default matches dbt duckdb profile local.
    """
    return _get_duckdb_medallion_schema(
        env_var_name="DBT_DUCKDB_MEDALLION_SCHEMA"
    )


def get_local_data_source() -> Literal["duckdb", "csv"]:
    """
    When data_source is 'local', prefer 'duckdb' (DuckDB medallion) if DBT_DUCKDB_PATH
    exists and is a file; otherwise 'csv' (data/local CSVs). Loaders fall back to CSV
    if DuckDB is chosen but tables are missing.
    """
    return _get_local_data_source(duckdb_path=get_duckdb_path())


def get_catalog_schema() -> str:
    """Unity Catalog schema for reco tables (e.g. workspace.healthcare_medallion). Override with RECO_CATALOG_SCHEMA."""
    return _get_catalog_schema(env_var_name="RECO_CATALOG_SCHEMA")


# MLflow tracking/artifact/experiment helpers: delegated to shared config (local vs Databricks)
# get_mlflow_tracking_uri, get_mlflow_artifact_root, ensure_experiment_artifact_root imported above


def get_mlflow_registry_uri() -> str | None:
    """
    MLflow registry URI: None when local, 'databricks-uc' on Databricks for Unity Catalog.
    Override with MLFLOW_REGISTRY_URI.
    """
    return _get_mlflow_registry_uri()


def apply_mlflow_config(config: dict | None = None) -> None:
    """
    Set MLflow tracking and registry URIs (local vs Databricks).
    Call before set_experiment/start_run so runs go to local SQLite or Databricks + UC.
    Delegates to utils.mlflow.config for consistency with inventory_optimization.
    config: ignored (kept for API compatibility).
    """
    _apply_mlflow_config(config)


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
