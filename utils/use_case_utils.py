"""
Shared helpers for resolving use-case configuration (local DuckDB/CSV vs
Unity Catalog) and locating local data artifacts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

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


def require_env_non_empty(env_var: str, *, detail: str) -> str:
    """
    Return stripped env value or raise RuntimeError referencing env_var.
    Use for Unity Catalog schema variables required in catalog mode.
    """
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        raise RuntimeError(f"{env_var} is required {detail}")
    return raw


def resolve_local_base_dir(
    *,
    primary_env: str,
    fallback_env: str = "LOCAL_DATA_PATH",
    default_path: Path,
) -> Path:
    """
    Prefer primary_env, else fallback_env with default_path when unset.
    Doc intelligence and similar: DOCINT_BASE_DIR vs LOCAL_DATA_PATH.
    """
    p = os.environ.get(primary_env) or os.environ.get(
        fallback_env, str(default_path.resolve())
    )
    return Path(p).resolve()


def get_env_str(name: str, default: str) -> str:
    """Strip env or default (non-empty default preserved)."""
    return (os.environ.get(name) or default).strip()


def build_medallion_use_case_config(
    *,
    data_source: Literal["local", "catalog"],
    local_data_dir: Path,
    local_data_source: Literal["duckdb", "csv"],
    duckdb_path: Path | None,
    duckdb_medallion_schema: str,
    uc_schema_fields: dict[str, str | None],
) -> dict[str, Any]:
    """
    Assemble the standard reco/inventory-style config dict (local DuckDB/CSV vs UC + MLflow).
    uc_schema_fields: use-case-specific nullable UC keys (e.g. input_silver_schema, output_schema).
    """
    return {
        "data_source": data_source,
        "local_data_dir": local_data_dir,
        "local_data_source": local_data_source,
        "duckdb_path": duckdb_path,
        "duckdb_medallion_schema": duckdb_medallion_schema,
        **uc_schema_fields,
        "on_databricks": is_running_on_databricks(),
        "mlflow_tracking_uri": _get_mlflow_tracking_uri(),
        "mlflow_registry_uri": _get_mlflow_registry_uri(),
    }


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

