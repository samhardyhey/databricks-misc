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

# High-throughput data generation strategy
# Base entities (pharmacies, hospitals) are relatively stable
# Transactional data (products, orders, inventory, events) changes frequently
BASE_ENTITY_SIZES = {
    "pharmacies": 50,    # Stable - only generate occasionally
    "hospitals": 25,     # Stable - only generate occasionally
}

# High-frequency transactional data (every 15 minutes)
# Adjusted to maintain same hourly volumes: 4 runs × 15min = 1 hour
TRANSACTIONAL_SIZES = {
    "products": 25,      # 25 × 4 = 100 products/hour
    "orders": 125,       # 125 × 4 = 500 orders/hour
    "inventory": 250,    # 250 × 4 = 1,000 inventory updates/hour
    "events": 50,        # 50 × 4 = 200 events/hour
}


class DatabricksHealthcareDataGenerator:
    """Databricks-specific wrapper for healthcare data generator with Unity Catalog integration."""

    def __init__(self, spark: SparkSession, seed: Optional[int] = None):
        """Initialize the data generator with Spark session."""
        self.spark = spark
        self.generator = HealthcareDataGenerator(seed=seed)

        logger.info(f"DatabricksHealthcareDataGenerator initialized with seed: {seed}")

    def save_to_catalog(
        self, df, table_name: str, mode: str = "append"
    ) -> None:
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
    # Initialize Spark session
    spark = SparkSession.builder.appName("HealthcareDataGeneration").getOrCreate()

    # Ensure schema exists
    ensure_schema_exists(spark)

    # Initialize data generator
    generator = DatabricksHealthcareDataGenerator(spark, seed=42)

    logger.info("🚀 Starting high-frequency healthcare data generation (15-minute cycle)...")

    # Check if base entities exist, if not create them
    base_entities_created = False
    try:
        spark.table(f"{CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_PREFIX}pharmacies").count()
        logger.info("📋 Base entities already exist, skipping creation")
    except:
        logger.info("📋 Creating base entities (pharmacies, hospitals)...")
        base_entities_created = True

        # Generate base entities (pharmacies, hospitals) - these are relatively stable
        pharmacies = generator.generator.generate_pharmacies(BASE_ENTITY_SIZES["pharmacies"])
        hospitals = generator.generator.generate_hospitals(BASE_ENTITY_SIZES["hospitals"])

        # Save base entities (overwrite mode for initial creation)
        generator.save_to_catalog(pharmacies, "pharmacies", mode="overwrite")
        generator.save_to_catalog(hospitals, "hospitals", mode="overwrite")

        logger.info(f"✅ Created {len(pharmacies)} pharmacies and {len(hospitals)} hospitals")

    # Always generate high-frequency transactional data
    logger.info("📊 Generating transactional data (products, orders, inventory, events)...")

    # Load existing base entities for foreign key relationships
    try:
        pharmacies_df = spark.table(f"{CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_PREFIX}pharmacies").toPandas()
        hospitals_df = spark.table(f"{CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_PREFIX}hospitals").toPandas()
        logger.info(f"📋 Loaded {len(pharmacies_df)} pharmacies and {len(hospitals_df)} hospitals for foreign keys")
    except Exception as e:
        logger.error(f"❌ Failed to load base entities: {e}")
        # Generate minimal base entities for this run
        logger.info("🔄 Generating minimal base entities for this run...")
        pharmacies_df = generator.generator.generate_pharmacies(5)
        hospitals_df = generator.generator.generate_hospitals(3)

    # Generate transactional data
    products = generator.generator.generate_products(TRANSACTIONAL_SIZES["products"])
    orders = generator.generator.generate_orders(
        TRANSACTIONAL_SIZES["orders"],
        pharmacies_df,
        hospitals_df,
        products
    )
    inventory = generator.generator.generate_inventory(
        TRANSACTIONAL_SIZES["inventory"],
        pharmacies_df,
        products
    )
    events = generator.generator.generate_supply_chain_events(
        TRANSACTIONAL_SIZES["events"],
        orders
    )

    # Save transactional data (append mode for incremental updates)
    datasets = {
        "products": products,
        "orders": orders,
        "inventory": inventory,
        "supply_chain_events": events,
    }

    for table_name, df in datasets.items():
        generator.save_to_catalog(df, table_name, mode="append")

    # Display summary
    logger.info("=== HIGH-FREQUENCY DATA GENERATION COMPLETE (15-min cycle) ===")
    total_records = 0
    for name, df in datasets.items():
        records = len(df)
        total_records += records
        logger.info(f"{name:20}: {records:6,} records (appended)")
    logger.info(f"{'TOTAL':20}: {total_records:6,} records")
    logger.info(f"📊 Hourly projection: {total_records * 4:,} records/hour")

    # Verify tables exist in catalog and show total counts
    logger.info("\n=== VERIFYING UNITY CATALOG TABLES ===")
    all_tables = ["pharmacies", "hospitals"] + list(datasets.keys())
    for table_name in all_tables:
        full_table_name = f"{CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_PREFIX}{table_name}"
        try:
            count = spark.table(full_table_name).count()
            logger.info(f"✓ {full_table_name}: {count:,} total records")
        except Exception as e:
            logger.error(f"✗ {full_table_name}: Error - {e}")

    return datasets


if __name__ == "__main__":
    datasets = main()
