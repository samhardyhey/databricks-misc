"""
Load inventory-optimisation data from local DuckDB medallion (preferred), local CSV,
or Unity Catalog; switch via config (config.get_config()).
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from use_cases.inventory_optimization.config import get_config


def _load_from_duckdb(duckdb_path: Path, base_schema: str) -> dict[str, pd.DataFrame | None]:
    """
    Load inventory, orders, products, expiry_batches, writeoff_events from local DuckDB medallion.
    dbt builds silver (and optionally bronze) in {base_schema}_silver, {base_schema}_bronze.
    """
    import duckdb  # type: ignore[import-untyped]

    out: dict[str, pd.DataFrame | None] = {}
    conn = duckdb.connect(str(duckdb_path), read_only=True)
    silver = f"{base_schema}_silver"
    bronze = f"{base_schema}_bronze"
    datetime_cols_inventory = ("expiry_date", "last_restocked", "last_movement_date", "updated_timestamp")
    try:
        for table, key in [
            (f"{silver}.silver_inventory", "inventory"),
            (f"{silver}.silver_orders", "orders"),
            (f"{silver}.silver_products", "products"),
        ]:
            try:
                df = conn.execute(f"SELECT * FROM {table}").fetchdf()
                if key == "inventory":
                    for col in datetime_cols_inventory:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], errors="coerce")
                elif key == "orders" and "order_date" in df.columns:
                    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
                out[key] = df
                logger.info("Loaded {} from DuckDB {}", key, table)
            except duckdb.CatalogException:
                out[key] = None
        out.setdefault("expiry_batches", None)
        out.setdefault("writeoff_events", None)
        for table_candidate, key in [
            (f"{silver}.silver_expiry_batches", "expiry_batches"),
            (f"{bronze}.bronze_expiry_batches", "expiry_batches"),
            (f"{silver}.silver_writeoff_events", "writeoff_events"),
            (f"{bronze}.bronze_writeoff_events", "writeoff_events"),
        ]:
            if key in out and out[key] is not None:
                continue
            try:
                df = conn.execute(f"SELECT * FROM {table_candidate}").fetchdf()
                if key == "expiry_batches" and "expiry_date" in df.columns:
                    df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")
                elif key == "writeoff_events" and "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                out[key] = df
                logger.info("Loaded {} from DuckDB {}", key, table_candidate)
            except duckdb.CatalogException:
                if key not in out:
                    out[key] = None
    finally:
        conn.close()
    return out


def _load_from_catalog(spark, catalog_schema: str) -> dict[str, pd.DataFrame | None]:
    """Load inventory, expiry_batches, writeoff_events, orders, products from Unity Catalog."""
    out = {}
    # Inventory (silver)
    table = f"{catalog_schema}.silver_inventory"
    logger.info("Loading inventory from {}", table)
    df = spark.table(table).toPandas()
    for col in (
        "expiry_date",
        "last_restocked",
        "last_movement_date",
        "updated_timestamp",
    ):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    out["inventory"] = df
    # Orders
    table = f"{catalog_schema}.silver_orders"
    logger.info("Loading orders from {}", table)
    df = spark.table(table).toPandas()
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    out["orders"] = df
    # Products
    table = f"{catalog_schema}.silver_products"
    logger.info("Loading products from {}", table)
    out["products"] = spark.table(table).toPandas()
    # Expiry batches (bronze/silver if present)
    for name in ("silver_expiry_batches", "bronze_expiry_batches"):
        try:
            df = spark.table(f"{catalog_schema}.{name}").toPandas()
            if "expiry_date" in df.columns:
                df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")
            out["expiry_batches"] = df
            logger.info("Loading expiry_batches from {}", f"{catalog_schema}.{name}")
            break
        except Exception:
            continue
    else:
        out["expiry_batches"] = None
    # Writeoff events (bronze/silver if present)
    for name in ("silver_writeoff_events", "bronze_writeoff_events"):
        try:
            df = spark.table(f"{catalog_schema}.{name}").toPandas()
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            out["writeoff_events"] = df
            logger.info("Loading writeoff_events from {}", f"{catalog_schema}.{name}")
            break
        except Exception:
            continue
    else:
        out["writeoff_events"] = None
    return out


def _load_from_local(data_dir: Path) -> dict[str, pd.DataFrame | None]:
    """Load inventory, expiry_batches, writeoff_events, orders, products from local CSV."""
    out = {}
    for name, path in [
        ("inventory", "inventory.csv"),
        ("expiry_batches", "expiry_batches.csv"),
        ("writeoff_events", "writeoff_events.csv"),
        ("orders", "orders.csv"),
        ("products", "products.csv"),
    ]:
        filepath = data_dir / path
        if filepath.exists():
            out[name] = pd.read_csv(filepath)
            if name == "inventory":
                for col in (
                    "expiry_date",
                    "last_restocked",
                    "last_movement_date",
                    "updated_timestamp",
                ):
                    if col in out[name].columns:
                        out[name][col] = pd.to_datetime(out[name][col], errors="coerce")
            elif name == "expiry_batches" and "expiry_date" in out[name].columns:
                out[name]["expiry_date"] = pd.to_datetime(
                    out[name]["expiry_date"], errors="coerce"
                )
            elif name == "writeoff_events" and "timestamp" in out[name].columns:
                out[name]["timestamp"] = pd.to_datetime(
                    out[name]["timestamp"], errors="coerce"
                )
            elif name == "orders" and "order_date" in out[name].columns:
                out[name]["order_date"] = pd.to_datetime(
                    out[name]["order_date"], errors="coerce"
                )
            logger.info("Loaded {} from {}", name, filepath)
        else:
            out[name] = None
    return out


def load_inventory_data(
    config: dict | None = None, spark=None
) -> dict[str, pd.DataFrame | None]:
    """
    Load all inventory data (inventory, orders, products, expiry_batches, writeoff_events).
    - catalog: Unity Catalog via spark and config["catalog_schema"].
    - local: prefer DuckDB medallion (config["duckdb_path"], config["duckdb_medallion_schema"])
      when config["local_data_source"] == "duckdb"; fall back to CSV from config["local_data_dir"].
    """
    cfg = config or get_config()
    if cfg["data_source"] == "catalog":
        if spark is None:
            raise RuntimeError(
                "data_source is 'catalog' but spark is None; create SparkSession on Databricks."
            )
        return _load_from_catalog(spark, cfg["catalog_schema"])
    # Local: try DuckDB medallion first when configured
    if cfg.get("local_data_source") == "duckdb" and cfg.get("duckdb_path"):
        try:
            data = _load_from_duckdb(
                Path(cfg["duckdb_path"]),
                cfg.get("duckdb_medallion_schema", "healthcare_medallion_local"),
            )
            if data.get("inventory") is not None and data.get("orders") is not None:
                return data
        except Exception as e:
            logger.warning("DuckDB medallion load failed, falling back to CSV: {}", e)
    data_dir = cfg["local_data_dir"] if isinstance(cfg["local_data_dir"], Path) else Path(cfg["local_data_dir"])
    return _load_from_local(data_dir)


def get_local_data_dir_default() -> Path:
    """Back-compat: default local data dir from config."""
    return get_config()["local_data_dir"]


def get_inventory_data(
    config: dict | None = None, spark=None
) -> dict[str, pd.DataFrame | None]:
    """Return inventory-related DataFrames. Uses load_inventory_data with config (default get_config())."""
    return load_inventory_data(config=config or get_config(), spark=spark)
