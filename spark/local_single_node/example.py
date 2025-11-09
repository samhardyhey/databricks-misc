"""
Example Spark script for local single-node development.

This demonstrates basic Spark operations in local mode.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, desc
from loguru import logger

# Create Spark session in local mode
# local[*] uses all CPU cores, or specify local[4] for 4 cores
spark = SparkSession.builder \
    .appName("LocalSparkExample") \
    .master("local[*]") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()

logger.info(f"Spark version: {spark.version}")
logger.info(f"Spark UI available at: http://localhost:4040")

# Create sample data
data = [
    ("Alice", 25, "Engineering"),
    ("Bob", 30, "Sales"),
    ("Charlie", 35, "Engineering"),
    ("Diana", 28, "Marketing"),
    ("Eve", 32, "Engineering"),
]

columns = ["name", "age", "department"]

# Create DataFrame
df = spark.createDataFrame(data, columns)
logger.info("Created sample DataFrame")

# Show the data
df.show()

# Basic transformations
logger.info("\n=== Basic Transformations ===")
df.select("name", "age").show()

# Filter
logger.info("\n=== Filtering ===")
df.filter(col("age") > 30).show()

# Group by and aggregate
logger.info("\n=== Aggregations ===")
df.groupBy("department") \
    .agg(
        count("*").alias("count"),
        avg("age").alias("avg_age")
    ) \
    .orderBy(desc("count")) \
    .show()

# Read from CSV (if you have data files)
# df = spark.read.csv("data/sample.csv", header=True, inferSchema=True)

# Write to parquet
# df.write.mode("overwrite").parquet("output/data.parquet")

logger.info("\n✅ Example completed successfully!")
logger.info("Check Spark UI at http://localhost:4040 for execution details")

# Stop Spark session
spark.stop()

