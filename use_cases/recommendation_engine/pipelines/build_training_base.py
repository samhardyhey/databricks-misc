"""
Build gold_reco_training_base from silver_reco_interactions (use-case-owned transform).

Replaces the former dbt medallion model; run via make reco-build-training-base (local)
or DAB job recommendation_engine_build_training_base (remote).

- Catalog: reads from medallion silver, writes to output_schema.gold_reco_training_base.
- Local: reads from DuckDB/CSV, writes to data/local/reco/gold_reco_training_base.parquet.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from use_cases.recommendation_engine.config import get_config

# Local output path when data_source is local (override with RECO_LOCAL_TRAINING_BASE_PATH).
DEFAULT_LOCAL_TRAINING_BASE_PATH = Path("data/local/reco/gold_reco_training_base.parquet")


def _compute_training_base(interactions: pd.DataFrame) -> pd.DataFrame:
    """Same logic as former dbt gold_reco_training_base: customer, product, label, timestamps."""
    if interactions is None or interactions.empty:
        raise ValueError("interactions is empty")
    df = interactions.copy()
    if "action_type" not in df.columns:
        raise ValueError("interactions must have action_type")
    ts_col = "interaction_timestamp" if "interaction_timestamp" in df.columns else "timestamp"
    if ts_col not in df.columns:
        raise ValueError(f"interactions must have {ts_col}")
    df["_label"] = (df["action_type"] == "purchased").astype(int)
    out = df.groupby(["customer_id", "product_id"], as_index=False).agg(
        label=("_label", "max"),
        last_interaction_timestamp=(ts_col, "max"),
        interaction_count=("customer_id", "count"),
    )
    return out


def _load_interactions_local(cfg: dict) -> pd.DataFrame:
    """Load silver_reco_interactions from DuckDB or CSV."""
    if cfg.get("local_data_source") == "duckdb" and cfg.get("duckdb_path"):
        import duckdb
        path = Path(cfg["duckdb_path"])
        if not path.is_file():
            raise FileNotFoundError(f"DuckDB not found: {path}. Run make reco-data.")
        base = cfg.get("duckdb_medallion_schema", "healthcare_medallion_local")
        silver = f"{base}_silver"
        conn = duckdb.connect(str(path), read_only=True)
        try:
            df = conn.execute(f"SELECT * FROM {silver}.silver_reco_interactions").fetchdf()
        except Exception as e:
            logger.warning("DuckDB silver_reco_interactions failed: {}", e)
            conn.close()
            raise
        conn.close()
        if "interaction_timestamp" not in df.columns and "timestamp" in df.columns:
            df["interaction_timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    # CSV fallback
    data_dir = cfg["local_data_dir"]
    if not isinstance(data_dir, Path):
        data_dir = Path(data_dir)
    path = data_dir / "product_interactions.csv"
    if not path.exists():
        raise FileNotFoundError(f"Interactions CSV not found: {path}. Run make reco-data.")
    df = pd.read_csv(path)
    if "interaction_timestamp" not in df.columns and "timestamp" in df.columns:
        df["interaction_timestamp"] = pd.to_datetime(df["timestamp"])
    if "action_type" not in df.columns:
        df["action_type"] = "purchased"
    return df


def main() -> dict:
    cfg = get_config()
    data_source = cfg["data_source"]
    logger.info("build_training_base: data_source={}", data_source)

    if data_source == "catalog":
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName("RecoBuildTrainingBase").getOrCreate()
        table_in = f"{cfg['input_silver_schema']}.silver_reco_interactions"
        logger.info("Loading interactions from {}", table_in)
        df = spark.table(table_in).toPandas()
        if "interaction_timestamp" not in df.columns and "timestamp" in df.columns:
            df["interaction_timestamp"] = pd.to_datetime(df["timestamp"])
        training_base = _compute_training_base(df)
        out_table = f"{cfg['output_schema']}.gold_reco_training_base"
        logger.info("Writing training base to {}", out_table)
        spark.createDataFrame(training_base).write.saveAsTable(out_table, mode="overwrite")
        return {"written": out_table, "rows": len(training_base)}

    # Local
    interactions = _load_interactions_local(cfg)
    training_base = _compute_training_base(interactions)
    out_path = Path(
        __import__("os").environ.get("RECO_LOCAL_TRAINING_BASE_PATH", str(DEFAULT_LOCAL_TRAINING_BASE_PATH))
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    training_base.to_parquet(out_path, index=False)
    logger.info("Wrote {} rows to {}", len(training_base), out_path)
    return {"written": str(out_path), "rows": len(training_base)}


if __name__ == "__main__":
    main()
