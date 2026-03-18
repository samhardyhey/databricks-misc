"""
Thin shim: re-export inventory data loading from models.data_loading.

All loaders use config (get_config()): when local, prefer DuckDB medallion
(DBT_DUCKDB_PATH) with CSV fallback so we use the medallions we create.
"""

from use_cases.inventory_optimization.models.data_loading import (
    get_inventory_data,
    get_local_data_dir_default,
    load_inventory_data,
)

__all__ = [
    "load_inventory_data",
    "get_inventory_data",
    "get_local_data_dir_default",
]
