"""
Databricks Unity Catalog Data Generation Script

This script generates healthcare/pharmaceutical distribution data and saves it
directly to the Databricks Unity Catalog for ML experimentation and analysis.

Usage: Run this script in a Databricks notebook or as a job.
"""

from typing import Dict, Optional

from loguru import logger

# Import the existing healthcare data generator
from healthcare_data_generator import HealthcareDataGenerator, DEFAULT_SIZES

# Databricks imports
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit

# Unity Catalog configuration
CATALOG_NAME = "workspace"
SCHEMA_NAME = "default"
TABLE_PREFIX = "healthcare_"


class DatabricksHealthcareDataGenerator:
    """Databricks-specific wrapper for healthcare data generator with Unity Catalog integration."""

    def __init__(self, spark: SparkSession, seed: Optional[int] = None):
        """Initialize the data generator with Spark session."""
        self.spark = spark
        self.generator = HealthcareDataGenerator(seed=seed)

        logger.info(f"DatabricksHealthcareDataGenerator initialized with seed: {seed}")

    def save_to_catalog(
        self, df, table_name: str, mode: str = "overwrite"
    ) -> None:
        """Save DataFrame to Unity Catalog."""
        full_table_name = f"{CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_PREFIX}{table_name}"

        logger.info(f"Saving {len(df)} records to {full_table_name}")

        # Convert pandas DataFrame to Spark DataFrame
        spark_df = self.spark.createDataFrame(df)

        # Add metadata columns
        spark_df = spark_df.withColumn("_ingestion_timestamp", current_timestamp())
        spark_df = spark_df.withColumn("_source", lit("healthcare_data_generator"))

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


def main():
    """Main function to generate and save healthcare data to Unity Catalog."""
    # Initialize Spark session
    spark = SparkSession.builder.appName("HealthcareDataGeneration").getOrCreate()

    # Initialize data generator
    generator = DatabricksHealthcareDataGenerator(spark, seed=42)

    # Generate datasets with default sizes
    datasets = generator.generate_all_datasets(
        n_pharmacies=DEFAULT_SIZES["pharmacies"],
        n_hospitals=DEFAULT_SIZES["hospitals"],
        n_products=DEFAULT_SIZES["products"],
        n_orders=DEFAULT_SIZES["orders"],
        n_inventory=DEFAULT_SIZES["inventory"],
        n_events=DEFAULT_SIZES["events"],
        save_to_catalog=True,
    )

    # Display summary
    logger.info("=== HEALTHCARE DATA GENERATION COMPLETE ===")
    total_records = 0
    for name, df in datasets.items():
        records = len(df)
        total_records += records
        logger.info(f"{name:20}: {records:6,} records")
    logger.info(f"{'TOTAL':20}: {total_records:6,} records")

    # Verify tables exist in catalog
    logger.info("\n=== VERIFYING UNITY CATALOG TABLES ===")
    for table_name in datasets.keys():
        full_table_name = f"{CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_PREFIX}{table_name}"
        try:
            count = spark.table(full_table_name).count()
            logger.info(f"✓ {full_table_name}: {count:,} records")
        except Exception as e:
            logger.error(f"✗ {full_table_name}: Error - {e}")

    return datasets


if __name__ == "__main__":
    datasets = main()
