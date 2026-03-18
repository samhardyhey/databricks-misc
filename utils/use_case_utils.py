"""
Shared helpers for resolving use-case configuration (local DuckDB/CSV vs
Unity Catalog) and locating local data artifacts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from utils.env_utils import is_running_on_databricks
from utils.mlflow.config import (
    apply_mlflow_config as _apply_mlflow_config,
    ensure_experiment_artifact_root as _ensure_experiment_artifact_root,
    get_mlflow_artifact_root as _get_mlflow_artifact_root,
    get_mlflow_registry_uri as _get_mlflow_registry_uri,
    get_mlflow_tracking_uri as _get_mlflow_tracking_uri,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Defaults (can be overridden via env vars)
DEFAULT_LOCAL_DATA_DIR = _REPO_ROOT / "data" / "local"
DEFAULT_CATALOG_SCHEMA = "workspace.healthcare_medallion"
DEFAULT_DUCKDB_MEDALLION_SCHEMA = "healthcare_medallion_local"
DEFAULT_DUCKDB_PATH = DEFAULT_LOCAL_DATA_DIR / "medallion.duckdb"


def resolve_data_source(
    *,
    env_var_name: str,
    default: Literal["auto"] = "auto",
) -> Literal["local", "catalog"]:
    """
    Resolve data source based on env.

    - env_var_name: 'local' | 'catalog' | 'auto'
    - 'auto' => 'catalog' on Databricks, else 'local'
    """
    raw = os.environ.get(env_var_name, default).strip().lower()
    if raw == "catalog":
        return "catalog"
    if raw == "local":
        return "local"
    # auto
    return "catalog" if is_running_on_databricks() else "local"


def get_local_data_dir(*, env_var_name: str = "LOCAL_DATA_PATH") -> Path:
    p = os.environ.get(env_var_name, str(DEFAULT_LOCAL_DATA_DIR))
    return Path(p).resolve()


def get_duckdb_path(
    *,
    env_var_name: str = "DBT_DUCKDB_PATH",
    duckdb_path_default: Path = DEFAULT_DUCKDB_PATH,
) -> Path | None:
    raw = os.environ.get(env_var_name)
    p = Path(raw).resolve() if raw else duckdb_path_default.resolve()
    return p if p.is_file() else None


def get_duckdb_medallion_schema(
    *, env_var_name: str = "DBT_DUCKDB_MEDALLION_SCHEMA"
) -> str:
    return os.environ.get(env_var_name, DEFAULT_DUCKDB_MEDALLION_SCHEMA).strip()


def get_catalog_schema(
    *, env_var_name: str = "RECO_CATALOG_SCHEMA", default: str = DEFAULT_CATALOG_SCHEMA
) -> str:
    """
    Note: Inventory uses INVENTORY_CATALOG_SCHEMA; reco uses RECO_CATALOG_SCHEMA.
    Both default to DEFAULT_CATALOG_SCHEMA.
    """
    return os.environ.get(env_var_name, default).strip()


def get_local_data_source(*, duckdb_path: Path | None) -> Literal["duckdb", "csv"]:
    return "duckdb" if duckdb_path is not None else "csv"


# --- MLflow (centralized) ---


def get_mlflow_tracking_uri() -> str | None:
    return _get_mlflow_tracking_uri()


def get_mlflow_registry_uri() -> str | None:
    return _get_mlflow_registry_uri()


def get_mlflow_artifact_root() -> str | None:
    return _get_mlflow_artifact_root()


def apply_mlflow_config(config: dict | None = None) -> None:
    # config is accepted for API compatibility with older wrappers.
    _apply_mlflow_config()


def ensure_experiment_artifact_root(experiment_name: str) -> None:
    _ensure_experiment_artifact_root(experiment_name)

