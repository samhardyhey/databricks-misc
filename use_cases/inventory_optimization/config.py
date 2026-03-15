"""
Inventory optimisation run config: data source (local CSV vs Unity Catalog) and paths.
Switch via INVENTORY_DATA_SOURCE and environment; same code path for train/eval.
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
    INVENTORY_DATA_SOURCE: 'local' | 'catalog' | 'auto'.
    - 'auto': use 'catalog' on Databricks (DATABRICKS_RUNTIME_VERSION set), else 'local'.
    - Explicit 'local'/'catalog' override (e.g. Databricks Connect + catalog).
    """
    raw = os.environ.get("INVENTORY_DATA_SOURCE", "auto").strip().lower()
    if raw == "catalog":
        return "catalog"
    if raw == "local":
        return "local"
    return "catalog" if is_running_on_databricks() else "local"


def get_local_data_dir() -> Path:
    """Directory for local CSVs (e.g. data/local). Override with LOCAL_DATA_PATH."""
    p = os.environ.get("LOCAL_DATA_PATH", str(_DEFAULT_LOCAL_DATA_DIR))
    return Path(p).resolve()


def get_catalog_schema() -> str:
    """Unity Catalog schema for inventory tables. Override with INVENTORY_CATALOG_SCHEMA."""
    return os.environ.get("INVENTORY_CATALOG_SCHEMA", _DEFAULT_CATALOG_SCHEMA)


def get_config() -> dict:
    """
    Single config dict for the inventory pipeline.
    - data_source: 'local' | 'catalog'
    - local_data_dir: Path (used when data_source == 'local')
    - catalog_schema: str (used when data_source == 'catalog')
    - on_databricks: bool (is_running_on_databricks())
    """
    data_source = get_data_source()
    return {
        "data_source": data_source,
        "local_data_dir": get_local_data_dir(),
        "catalog_schema": get_catalog_schema(),
        "on_databricks": is_running_on_databricks(),
    }
