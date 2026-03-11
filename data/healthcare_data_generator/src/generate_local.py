"""
Generate healthcare datasets to local CSV (e.g. data/local/) for local dev and medallion.
Invoke from repo root: make data-local-generate  or  python data/healthcare_data_generator/src/generate_local.py --output-dir data/local
"""

import argparse
from pathlib import Path

from loguru import logger

from data.healthcare_data_generator.src.healthcare_data_generator import (
    DEFAULT_SIZES, HealthcareDataGenerator)


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
            "suppliers": 8,
            "products": 50,
            "orders": 100,
            "inventory": 200,
            "events": 50,
            "product_interactions_extra": 150,
            "substitution_ratio": 0.1,
            "purchase_orders": 30,
            "writeoff_events": 10,
            "competitor_products": 20,
            "store_sales_days": 30,
            "promotions": 15,
        }
        if args.quick
        else {
            **DEFAULT_SIZES,
            "product_interactions_extra": DEFAULT_SIZES.get("product_interactions", 15000) - 1000,
            "substitution_ratio": DEFAULT_SIZES.get("substitution_events_ratio", 0.1),
            "purchase_orders": DEFAULT_SIZES.get("purchase_orders", 3000),
            "writeoff_events": DEFAULT_SIZES.get("writeoff_events", 500),
            "competitor_products": DEFAULT_SIZES.get("competitor_products", 200),
            "store_sales_days": DEFAULT_SIZES.get("store_sales_days", 90),
            "promotions": DEFAULT_SIZES.get("promotions", 200),
        }
    )

    generator = HealthcareDataGenerator(seed=args.seed)
    datasets = generator.generate_all_datasets(
        n_pharmacies=sizes["pharmacies"],
        n_hospitals=sizes["hospitals"],
        n_suppliers=sizes.get("suppliers", DEFAULT_SIZES.get("suppliers", 80)),
        n_products=sizes["products"],
        n_orders=sizes["orders"],
        n_inventory=sizes["inventory"],
        n_events=sizes["events"],
        n_product_interactions_extra=sizes.get("product_interactions_extra", 5000),
        substitution_ratio=sizes.get("substitution_ratio", 0.1),
        n_purchase_orders=sizes.get("purchase_orders", 3000),
        n_writeoff_events=sizes.get("writeoff_events", 500),
        n_competitor_products=sizes.get("competitor_products", 200),
        store_sales_days=sizes.get("store_sales_days", 90),
        n_promotions=sizes.get("promotions", 200),
    )
    generator.save_datasets(datasets, output_dir=str(output_dir))
    logger.info(f"Local healthcare CSVs written to {output_dir.absolute()}")


if __name__ == "__main__":
    main()
