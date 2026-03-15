"""
Load reco data from Unity Catalog (Databricks) or local CSV.
"""

import os
from pathlib import Path

import pandas as pd
from loguru import logger

from use_cases.env_utils import is_running_on_databricks

DEFAULT_LOCAL_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "local"


def _catalog_schema() -> str:
    return os.environ.get("RECO_CATALOG_SCHEMA", "workspace.healthcare_medallion")


def load_interactions_from_catalog(spark) -> pd.DataFrame:
    """Load silver_reco_interactions from Unity Catalog."""
    table = f"{_catalog_schema()}.silver_reco_interactions"
    logger.info(f"Loading interactions from {table}")
    df = spark.table(table).toPandas()
    if "interaction_timestamp" in df.columns:
        df["interaction_timestamp"] = pd.to_datetime(df["interaction_timestamp"])
    return df


def load_training_base_from_catalog(spark) -> pd.DataFrame:
    """Load gold_reco_training_base from Unity Catalog."""
    table = f"{_catalog_schema()}.gold_reco_training_base"
    logger.info(f"Loading training base from {table}")
    return spark.table(table).toPandas()


def load_products_from_catalog(spark) -> pd.DataFrame:
    """Load silver_products from Unity Catalog."""
    table = f"{_catalog_schema()}.silver_products"
    logger.info(f"Loading products from {table}")
    return spark.table(table).toPandas()


def load_orders_from_catalog(spark) -> pd.DataFrame:
    """Load silver_orders from Unity Catalog."""
    table = f"{_catalog_schema()}.silver_orders"
    logger.info(f"Loading orders from {table}")
    df = spark.table(table).toPandas()
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def load_reco_data_local(data_dir: Path | None = None) -> dict[str, pd.DataFrame | None]:
    """Load interactions, products, orders from local CSV. Returns dict; missing files yield None."""
    data_dir = data_dir or Path(os.environ.get("LOCAL_DATA_PATH", str(DEFAULT_LOCAL_DATA_DIR)))
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
            logger.info(f"Loaded {name} from {data_dir / path}")
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


def get_training_base_and_products(spark=None):
    """Return (training_base_df, products_df). On Databricks uses spark; locally uses CSV."""
    if is_running_on_databricks() and spark is not None:
        training_base = load_training_base_from_catalog(spark)
        products = load_products_from_catalog(spark)
        return training_base, products
    data = load_reco_data_local()
    training_base = data.get("training_base")
    products = data.get("products")
    if training_base is None or products is None:
        raise FileNotFoundError(
            "Local data missing. Run generator and save to data/local/ or set LOCAL_DATA_PATH. "
            "Need product_interactions.csv and products.csv."
        )
    return training_base, products
