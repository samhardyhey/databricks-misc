"""
Load data/local/*.csv into DuckDB as schema healthcare_dev_raw (tables healthcare_*).
Run from repo root so paths resolve. Used by make data-local-dbt-run so dbt has raw sources.
"""
import argparse
import os
from pathlib import Path

import duckdb
from loguru import logger

# CSV filename (from generator) -> dbt source table name
CSV_TO_SOURCE = {
    "pharmacies": "healthcare_pharmacies",
    "hospitals": "healthcare_hospitals",
    "products": "healthcare_products",
    "orders": "healthcare_orders",
    "inventory": "healthcare_inventory",
    "supply_chain_events": "healthcare_supply_chain_events",
}

RAW_SCHEMA = "healthcare_dev_raw"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load data/local CSVs into DuckDB as raw schema for local dbt"
    )
    parser.add_argument(
        "--csv-dir",
        type=str,
        default=None,
        help=f"Directory containing CSVs (default: $REPO_ROOT/data/local or data/local)",
    )
    parser.add_argument(
        "--duckdb-path",
        type=str,
        default=None,
        help="DuckDB file path (default: DBT_DUCKDB_PATH env or data/local/medallion.duckdb)",
    )
    args = parser.parse_args()

    repo_root = Path(os.environ.get("REPO_ROOT", ".")).resolve()
    if not (repo_root / "data" / "local").is_dir():
        repo_root = Path(__file__).resolve().parent.parent.parent  # medallion -> data -> repo
    csv_dir = Path(args.csv_dir) if args.csv_dir else (repo_root / "data" / "local")
    csv_dir = csv_dir.resolve()

    duckdb_path = args.duckdb_path or os.environ.get(
        "DBT_DUCKDB_PATH", str(repo_root / "data" / "local" / "medallion.duckdb")
    )
    duckdb_path = str(Path(duckdb_path).resolve())

    if not csv_dir.is_dir():
        raise SystemExit(f"CSV dir not found: {csv_dir}. Run: make data-local-generate-quick")

    missing = [f"{name}.csv" for name in CSV_TO_SOURCE if not (csv_dir / f"{name}.csv").exists()]
    if missing:
        raise SystemExit(f"Missing CSVs in {csv_dir}: {missing}. Run: make data-local-generate-quick")

    csv_dir_str = str(csv_dir)
    conn = duckdb.connect(duckdb_path)
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")

    for csv_name, table_name in CSV_TO_SOURCE.items():
        path = csv_dir / f"{csv_name}.csv"
        # Add lineage columns expected by bronze models (Databricks ingest adds these; local CSV does not)
        conn.execute(
            f"""CREATE OR REPLACE TABLE {RAW_SCHEMA}.{table_name} AS
            SELECT *, now() AS _ingestion_timestamp, 'local_csv' AS _source, 'local' AS _batch_id
            FROM read_csv_auto(?)""",
            [str(path)],
        )
        n = conn.execute(f"SELECT COUNT(*) FROM {RAW_SCHEMA}.{table_name}").fetchone()[0]
        logger.info(f"Loaded {RAW_SCHEMA}.{table_name} <- {path.name} ({n} rows)")

    conn.close()
    logger.info(f"DuckDB raw layer ready: {duckdb_path}")


if __name__ == "__main__":
    main()
