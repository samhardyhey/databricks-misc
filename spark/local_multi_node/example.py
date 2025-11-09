"""
Example script to connect to Docker-based Spark cluster.

This demonstrates connecting to a multi-node Spark cluster from your local machine.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, desc, rand
from loguru import logger
import time

# Connect to the Docker-based Spark cluster
# Master URL matches the spark-master service in docker-compose.yml
spark = SparkSession.builder \
    .appName("MultiNodeSparkExample") \
    .master("spark://localhost:7077") \
    .config("spark.executor.memory", "1g") \
    .config("spark.executor.cores", "2") \
    .config("spark.cores.max", "4") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()

logger.info(f"Spark version: {spark.version}")
logger.info(f"Connected to cluster: spark://localhost:7077")
logger.info(f"Spark UI available at: http://localhost:4040")

# Check cluster info
sc = spark.sparkContext
logger.info(f"Default parallelism: {sc.defaultParallelism}")
logger.info(f"Spark master: {sc.master}")

# Create larger sample data to see distributed processing
logger.info("\n=== Creating sample data ===")
data = []
for i in range(1000):
    data.append((
        f"User_{i % 100}",
        i % 50 + 20,
        ["Engineering", "Sales", "Marketing", "Support"][i % 4],
        round(50000 + (i % 50000), 2)
    ))

columns = ["name", "age", "department", "salary"]
df = spark.createDataFrame(data, columns)

# Repartition to see distribution across workers
df = df.repartition(8)  # 8 partitions across 2 workers
logger.info(f"DataFrame partitions: {df.rdd.getNumPartitions()}")

# Show basic operations
logger.info("\n=== Basic Operations ===")
df.show(10)

# Aggregations (will trigger shuffle across workers)
logger.info("\n=== Aggregations (Distributed) ===")
result = df.groupBy("department") \
    .agg(
        count("*").alias("count"),
        avg("age").alias("avg_age"),
        avg("salary").alias("avg_salary")
    ) \
    .orderBy(desc("count"))

result.show()

# Check execution plan
logger.info("\n=== Execution Plan ===")
result.explain(True)

# More complex operation - join with self
logger.info("\n=== Complex Operations ===")
df1 = df.select("name", "department").distinct()
df2 = df.select("name", "age").distinct()
joined = df1.join(df2, on="name", how="inner")
logger.info(f"Join result count: {joined.count()}")

# Write to parquet (distributed write)
logger.info("\n=== Writing to Parquet (Distributed) ===")
output_path = "data/output/example_output"
df.write.mode("overwrite").parquet(output_path)
logger.info(f"Data written to: {output_path}")

# Read back
logger.info("\n=== Reading from Parquet ===")
df_read = spark.read.parquet(output_path)
logger.info(f"Read back {df_read.count()} rows")

logger.info("\n✅ Example completed successfully!")
logger.info("Check Spark UI at http://localhost:4040 to see distributed execution")
logger.info("Check Master UI at http://localhost:8080 to see cluster status")

# Stop Spark session
spark.stop()

