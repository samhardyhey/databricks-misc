"""
Load reco data from local CSV or Unity Catalog; switch via config (config.get_config()).
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import get_config


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
                out[name]["interaction_timestamp"] = pd.to_datetime(out[name]["timestamp"])
            elif name == "orders" and "order_date" in out[name].columns:
                out[name]["order_date"] = pd.to_datetime(out[name]["order_date"])
            logger.info("Loaded {} from {}", name, data_dir / path)
        else:
            out[name] = None
    if out.get("interactions") is not None and out.get("training_base") is None:
        df = out["interactions"].copy()
        if "action_type" in df.columns:
            ts = "interaction_timestamp" if "interaction_timestamp" in df.columns else "timestamp"
            df["_label"] = (df["action_type"] == "purchased").astype(int)
            out["training_base"] = df.groupby(["customer_id", "product_id"], as_index=False).agg(
                label=("_label", "max"),
                last_interaction_timestamp=(ts, "max"),
                interaction_count=("customer_id", "count"),
            )
    return out


def load_reco_data(config: dict | None = None, spark=None) -> dict[str, pd.DataFrame | None]:
    """
    Load all reco data (interactions, products, orders, training_base).
    Uses config["data_source"]: 'local' -> CSV from config["local_data_dir"];
    'catalog' -> Unity Catalog via spark and config["catalog_schema"].
    config defaults to get_config().
    """
    from pathlib import Path

    cfg = config or get_config()
    if cfg["data_source"] == "catalog":
        if spark is None:
            raise RuntimeError("data_source is 'catalog' but spark is None; create SparkSession on Databricks.")
        return _load_from_catalog(spark, cfg["catalog_schema"])
    return _load_from_local(cfg["local_data_dir"] if isinstance(cfg["local_data_dir"], Path) else Path(cfg["local_data_dir"]))


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
