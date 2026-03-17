"""
Load reco data from local DuckDB medallion (preferred), local CSV, or Unity Catalog;
switch via config (config.get_config()).
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import get_config


def _load_from_duckdb(
    duckdb_path: Path, base_schema: str
) -> dict[str, pd.DataFrame | None]:
    """
    Load interactions, products, orders, training_base from local DuckDB medallion.
    dbt builds silver/gold in {base_schema}_silver and {base_schema}_gold.
    """
    import duckdb  # type: ignore[import-untyped]

    out: dict[str, pd.DataFrame | None] = {}
    conn = duckdb.connect(str(duckdb_path), read_only=True)
    silver = f"{base_schema}_silver"
    gold = f"{base_schema}_gold"
    try:
        # silver_reco_interactions (may not exist in all medallions; fallback to product_interactions from raw)
        for table, key in [
            (f"{silver}.silver_reco_interactions", "interactions"),
            (f"{silver}.silver_products", "products"),
            (f"{silver}.silver_orders", "orders"),
        ]:
            try:
                df = conn.execute(f"SELECT * FROM {table}").fetchdf()
                if (
                    key == "interactions"
                    and "interaction_timestamp" not in df.columns
                    and "timestamp" in df.columns
                ):
                    df["interaction_timestamp"] = pd.to_datetime(df["timestamp"])
                elif key == "orders" and "order_date" in df.columns:
                    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
                out[key] = df
                logger.info("Loaded {} from DuckDB {}", key, table)
            except duckdb.CatalogException:
                out[key] = None
        # gold_reco_training_base
        try:
            out["training_base"] = conn.execute(
                f"SELECT * FROM {gold}.gold_reco_training_base"
            ).fetchdf()
            logger.info(
                "Loaded training_base from DuckDB {}.gold_reco_training_base", gold
            )
        except duckdb.CatalogException:
            out["training_base"] = None
    finally:
        conn.close()
    return out


def _load_from_catalog(spark, catalog_schema: str) -> dict[str, pd.DataFrame | None]:
    """Load interactions, products, orders, training_base from Unity Catalog."""
    out = {}
    # Interactions (silver)
    table = f"{catalog_schema}.silver_reco_interactions"
    logger.info("Loading interactions from {}", table)
    df = spark.table(table).toPandas()
    if "interaction_timestamp" in df.columns:
        df["interaction_timestamp"] = pd.to_datetime(df["interaction_timestamp"])
    out["interactions"] = df
    # Products
    table = f"{catalog_schema}.silver_products"
    logger.info("Loading products from {}", table)
    out["products"] = spark.table(table).toPandas()
    # Orders (optional)
    table = f"{catalog_schema}.silver_orders"
    try:
        df = spark.table(table).toPandas()
        if "order_date" in df.columns:
            df["order_date"] = pd.to_datetime(df["order_date"])
        out["orders"] = df
    except Exception:
        out["orders"] = None
    # Training base (gold)
    table = f"{catalog_schema}.gold_reco_training_base"
    logger.info("Loading training base from {}", table)
    out["training_base"] = spark.table(table).toPandas()
    return out


def _load_from_local(data_dir: Path) -> dict[str, pd.DataFrame | None]:
    """Load interactions, products, orders from local CSV; build training_base from interactions if missing."""
    out = {}
    for name, path in [
        ("interactions", "product_interactions.csv"),
        ("products", "products.csv"),
        ("orders", "orders.csv"),
        ("training_base", None),
    ]:
        if path and (data_dir / path).exists():
            out[name] = pd.read_csv(data_dir / path)
            if name == "interactions" and "timestamp" in out[name].columns:
                out[name]["interaction_timestamp"] = pd.to_datetime(
                    out[name]["timestamp"]
                )
            elif name == "orders" and "order_date" in out[name].columns:
                out[name]["order_date"] = pd.to_datetime(out[name]["order_date"])
            logger.info("Loaded {} from {}", name, data_dir / path)
        else:
            out[name] = None
    if out.get("interactions") is not None and out.get("training_base") is None:
        df = out["interactions"].copy()
        if "action_type" in df.columns:
            ts = (
                "interaction_timestamp"
                if "interaction_timestamp" in df.columns
                else "timestamp"
            )
            df["_label"] = (df["action_type"] == "purchased").astype(int)
            out["training_base"] = df.groupby(
                ["customer_id", "product_id"], as_index=False
            ).agg(
                label=("_label", "max"),
                last_interaction_timestamp=(ts, "max"),
                interaction_count=("customer_id", "count"),
            )
    return out


def load_reco_data(
    config: dict | None = None, spark=None
) -> dict[str, pd.DataFrame | None]:
    """
    Load all reco data (interactions, products, orders, training_base).
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
            if data.get("products") is not None and (
                data.get("training_base") is not None
                or data.get("interactions") is not None
            ):
                if (
                    data.get("training_base") is None
                    and data.get("interactions") is not None
                ):
                    df = data["interactions"].copy()
                    if "action_type" in df.columns:
                        ts = (
                            "interaction_timestamp"
                            if "interaction_timestamp" in df.columns
                            else "timestamp"
                        )
                        df["_label"] = (df["action_type"] == "purchased").astype(int)
                        data["training_base"] = df.groupby(
                            ["customer_id", "product_id"], as_index=False
                        ).agg(
                            label=("_label", "max"),
                            last_interaction_timestamp=(ts, "max"),
                            interaction_count=("customer_id", "count"),
                        )
                return data
        except Exception as e:
            logger.warning("DuckDB medallion load failed, falling back to CSV: {}", e)
    data_dir = (
        cfg["local_data_dir"]
        if isinstance(cfg["local_data_dir"], Path)
        else Path(cfg["local_data_dir"])
    )
    return _load_from_local(data_dir)


# Back-compat
def get_local_data_dir_default() -> Path:
    from use_cases.recommendation_engine.config import get_local_data_dir

    return get_local_data_dir()


def get_training_base_and_products(config: dict | None = None, spark=None):
    """Return (training_base_df, products_df). Uses load_reco_data with config."""
    data = load_reco_data(config=config, spark=spark)
    tb = data.get("training_base")
    products = data.get("products")
    if tb is None or products is None:
        raise FileNotFoundError(
            "Reco data missing. Local: run make reco-data and set LOCAL_DATA_PATH if needed. "
            "Catalog: set RECO_DATA_SOURCE=catalog and ensure medallion tables exist."
        )
    return tb, products
