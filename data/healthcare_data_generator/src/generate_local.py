"""
Generate healthcare datasets to local CSV (e.g. data/local/) for local dev and medallion.
Invoke from repo root: make data-local-generate  or  python data/healthcare_data_generator/src/generate_local.py --output-dir data/local
"""

import argparse
from pathlib import Path

from loguru import logger

from data.healthcare_data_generator.src.healthcare_data_generator import (
    DEFAULT_SIZES,
    HealthcareDataGenerator,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate healthcare CSVs for local dev (e.g. data/local/)"
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="data/local",
        help="Output directory for CSV files (default: data/local)",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use smaller sizes for fast iteration",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sizes = (
        {
            "pharmacies": 10,
            "hospitals": 5,
            "products": 50,
            "orders": 100,
            "inventory": 200,
            "events": 50,
        }
        if args.quick
        else DEFAULT_SIZES
    )

    generator = HealthcareDataGenerator(seed=args.seed)
    datasets = generator.generate_all_datasets(
        n_pharmacies=sizes["pharmacies"],
        n_hospitals=sizes["hospitals"],
        n_products=sizes["products"],
        n_orders=sizes["orders"],
        n_inventory=sizes["inventory"],
        n_events=sizes["events"],
    )
    generator.save_datasets(datasets, output_dir=str(output_dir))
    logger.info(f"Local healthcare CSVs written to {output_dir.absolute()}")


if __name__ == "__main__":
    main()
