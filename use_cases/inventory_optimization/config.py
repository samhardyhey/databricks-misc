"""
Inventory optimisation run config: data source (local CSV vs Unity Catalog) and paths.
Switch via INVENTORY_DATA_SOURCE and environment; same code path for train/eval.
MLflow: see utils.mlflow.config (local SQLite vs Databricks workspace).
"""

from pathlib import Path
from typing import Literal

from utils.env_utils import is_running_on_databricks
from utils.use_case_utils import apply_mlflow_config as _apply_mlflow_config
from utils.use_case_utils import (
    ensure_experiment_artifact_root as _ensure_experiment_artifact_root,
)
from utils.use_case_utils import get_catalog_schema as _get_catalog_schema
from utils.use_case_utils import (
    get_duckdb_medallion_schema as _get_duckdb_medallion_schema,
)
from utils.use_case_utils import get_duckdb_path as _get_duckdb_path
from utils.use_case_utils import get_local_data_dir as _get_local_data_dir
from utils.use_case_utils import get_local_data_source as _get_local_data_source
from utils.use_case_utils import (
    get_mlflow_registry_uri,
    get_mlflow_tracking_uri,
    resolve_data_source,
)

DataSource = Literal["local", "catalog", "auto"]


def get_data_source() -> Literal["local", "catalog"]:
    """
    Resolved data source: 'local' (CSV) or 'catalog' (Unity Catalog).
    INVENTORY_DATA_SOURCE: 'local' | 'catalog' | 'auto'.
    - 'auto': use 'catalog' on Databricks (DATABRICKS_RUNTIME_VERSION set), else 'local'.
    - Explicit 'local'/'catalog' override (e.g. Databricks Connect + catalog).
    """
    return resolve_data_source(env_var_name="INVENTORY_DATA_SOURCE")


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
    return _get_duckdb_medallion_schema(env_var_name="DBT_DUCKDB_MEDALLION_SCHEMA")


def get_local_data_source() -> Literal["duckdb", "csv"]:
    """
    When data_source is 'local', prefer 'duckdb' if DBT_DUCKDB_PATH exists and is a file;
    otherwise 'csv'. Loaders fall back to CSV if DuckDB is chosen but tables are missing.
    """
    return _get_local_data_source(duckdb_path=get_duckdb_path())


def get_catalog_schema() -> str:
    """Unity Catalog schema for inventory tables. Override with INVENTORY_CATALOG_SCHEMA."""
    return _get_catalog_schema(env_var_name="INVENTORY_CATALOG_SCHEMA")


# MLflow tracking/artifact/experiment: delegated to utils.mlflow.config (local vs Databricks)
# get_mlflow_tracking_uri, get_mlflow_artifact_root, ensure_experiment_artifact_root imported above


def get_config() -> dict:
    """
    Single config dict for the inventory pipeline.
    - data_source: 'local' | 'catalog'
    - local_data_dir: Path (used when data_source == 'local', CSV fallback)
    - local_data_source: 'duckdb' | 'csv' (when data_source == 'local': prefer DuckDB medallion)
    - duckdb_path: Path | None (when local and DuckDB file exists)
    - duckdb_medallion_schema: str (base schema for DuckDB)
    - catalog_schema: str (used when data_source == 'catalog')
    - on_databricks: bool (is_running_on_databricks())
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


def apply_mlflow_config(config: dict | None = None) -> None:
    """
    Back-compat wrapper for older callers importing from
    `use_cases.inventory_optimization.config`.
    """

    _apply_mlflow_config(config)


def ensure_experiment_artifact_root(experiment_name: str) -> None:
    """
    Back-compat wrapper for older callers importing from
    `use_cases.inventory_optimization.config`.
    """

    _ensure_experiment_artifact_root(experiment_name)
