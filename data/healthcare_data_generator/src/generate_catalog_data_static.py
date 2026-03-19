"""
Databricks Unity Catalog Data Generation Script

This script generates healthcare/pharmaceutical distribution data and saves it
directly to the Databricks Unity Catalog for ML experimentation and analysis.

Usage: Run this script in a Databricks notebook or as a job.
"""

# Unity Catalog configuration (override via bundle env: CATALOG_NAME, SCHEMA_NAME)
import os
from typing import Dict, Optional

# Import the existing healthcare data generator
from healthcare_data_generator import HealthcareDataGenerator
from loguru import logger

# Databricks imports
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit

TABLE_PREFIX = "healthcare_"
BUNDLE_TARGET = os.getenv("BUNDLE_TARGET", "dev")
CATALOG_NAME = os.getenv("CATALOG_NAME", "ebos_uc_demo")
SCHEMA_NAME = os.getenv("SCHEMA_NAME") or f"healthcare_{BUNDLE_TARGET}_raw"

# Large-scale data generation for ML experimentation
# One-time run with substantial dataset sizes
BASE_ENTITY_SIZES = {
    "pharmacies": 500,  # Large base of pharmacies
    "hospitals": 200,  # Large base of hospitals
}

# Large-scale transactional data for ML training
TRANSACTIONAL_SIZES = {
    "products": 5000,  # Large product catalog
    "orders": 25000,  # High volume of orders for ML training
    "inventory": 50000,  # Extensive inventory data
    "events": 10000,  # Rich event history
}


class DatabricksHealthcareDataGenerator:
    """Databricks-specific wrapper for healthcare data generator with Unity Catalog integration."""

    def __init__(self, spark: SparkSession, seed: Optional[int] = None):
        """Initialize the data generator with Spark session."""
        self.spark = spark
        self.generator = HealthcareDataGenerator(seed=seed)

        logger.info(f"DatabricksHealthcareDataGenerator initialized with seed: {seed}")
        logger.info(f"Target environment: {BUNDLE_TARGET}")
        logger.info(f"Target schema: {CATALOG_NAME}.{SCHEMA_NAME}")

    def save_to_catalog(self, df, table_name: str, mode: str = "append") -> None:
        """Save DataFrame to Unity Catalog."""
        full_table_name = f"{CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_PREFIX}{table_name}"

        logger.info(f"Saving {len(df)} records to {full_table_name} (mode: {mode})")

        # Convert pandas DataFrame to Spark DataFrame
        spark_df = self.spark.createDataFrame(df)

        # Add metadata columns
        import time

        batch_id = f"batch_{int(time.time())}"
        spark_df = spark_df.withColumn("_ingestion_timestamp", current_timestamp())
        spark_df = spark_df.withColumn("_source", lit("healthcare_data_generator"))
        spark_df = spark_df.withColumn("_batch_id", lit(batch_id))

        # Write to Unity Catalog
        spark_df.write.mode(mode).saveAsTable(full_table_name)

        logger.info(f"Successfully saved to {full_table_name}")

    def generate_all_datasets(
        self,
        n_pharmacies: int = 100,
        n_hospitals: int = 50,
        n_products: int = 1000,
        n_orders: int = 5000,
        n_inventory: int = 10000,
        n_events: int = 2000,
        save_to_catalog: bool = True,
    ) -> Dict[str, any]:
        """Generate all datasets and optionally save to Unity Catalog."""
        logger.info("Generating complete healthcare dataset...")

        # Use the existing generator to create all datasets
        datasets = self.generator.generate_all_datasets(
            n_pharmacies=n_pharmacies,
            n_hospitals=n_hospitals,
            n_products=n_products,
            n_orders=n_orders,
            n_inventory=n_inventory,
            n_events=n_events,
        )

        if save_to_catalog:
            logger.info("Saving datasets to Unity Catalog...")
            for table_name, df in datasets.items():
                self.save_to_catalog(df, table_name)

        logger.info("Dataset generation completed successfully!")
        return datasets


def ensure_schema_exists(spark):
    """Ensure the schema exists in Unity Catalog."""
    try:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG_NAME}.{SCHEMA_NAME}")
        logger.info(f"✅ Schema {CATALOG_NAME}.{SCHEMA_NAME} is ready")
    except Exception as e:
        logger.warning(f"⚠️ Could not create schema: {e}")


def main():
    """Main function to generate and save healthcare data to Unity Catalog."""
    # Install required dependencies
    import subprocess
    import sys

    try:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "faker>=24.0.0",
                "pandas>=2.2.0",
                "numpy>=1.24.0,<2.0.0",
                "pyarrow>=4.0.0,<15.0.0",
                "loguru>=0.7.2",
            ]
        )
        logger.info("✅ Dependencies installed successfully")
    except Exception as e:
        logger.warning(f"⚠️ Could not install dependencies: {e}")

    # Initialize Spark session
    spark = SparkSession.builder.appName("HealthcareDataGeneration").getOrCreate()

    # Ensure schema exists
    ensure_schema_exists(spark)

    # Initialize data generator
    generator = DatabricksHealthcareDataGenerator(spark, seed=42)

    logger.info(
        f"🚀 Starting large-scale healthcare data generation for ML experimentation..."
    )
    logger.info(f"🎯 Target environment: {BUNDLE_TARGET}")
    logger.info(f"📁 Target schema: {CATALOG_NAME}.{SCHEMA_NAME}")

    # Generate all datasets (base + use-case tables) in one pass
    logger.info("📊 Generating full healthcare dataset (base + use-case tables)...")
    n_pharmacies = BASE_ENTITY_SIZES["pharmacies"]
    n_hospitals = BASE_ENTITY_SIZES["hospitals"]
    n_suppliers = 80
    datasets = generator.generator.generate_all_datasets(
        n_pharmacies=n_pharmacies,
        n_hospitals=n_hospitals,
        n_suppliers=n_suppliers,
        n_products=TRANSACTIONAL_SIZES["products"],
        n_orders=TRANSACTIONAL_SIZES["orders"],
        n_inventory=TRANSACTIONAL_SIZES["inventory"],
        n_events=TRANSACTIONAL_SIZES["events"],
        n_product_interactions_extra=10000,
        substitution_ratio=0.1,
        n_purchase_orders=3000,
        n_writeoff_events=500,
        n_competitor_products=200,
        store_sales_days=90,
        n_promotions=200,
    )

    # Save all tables to catalog (overwrite so each run is full refresh)
    for table_name, df in datasets.items():
        generator.save_to_catalog(df, table_name, mode="overwrite")

    # Display summary
    logger.info("=== FULL HEALTHCARE DATA GENERATION COMPLETE ===")
    total_records = 0
    for name, df in datasets.items():
        records = len(df)
        total_records += records
        logger.info(f"{name:25}: {records:6,} records")
    logger.info(f"{'TOTAL':25}: {total_records:6,} records")
    logger.info("🎯 All use-case tables ready for ML and medallion.")

    # Verify tables exist in catalog and show total counts
    logger.info("\n=== VERIFYING UNITY CATALOG TABLES ===")
    for table_name in datasets.keys():
        full_table_name = f"{CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_PREFIX}{table_name}"
        try:
            count = spark.table(full_table_name).count()
            logger.info(f"✓ {full_table_name}: {count:,} total records")
        except Exception as e:
            logger.error(f"✗ {full_table_name}: Error - {e}")

    return datasets


if __name__ == "__main__":
    datasets = main()
