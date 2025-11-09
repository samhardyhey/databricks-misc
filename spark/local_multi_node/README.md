# Local Multi-Node Spark Cluster (Docker)

This setup runs a real Spark cluster using Docker containers - perfect for learning distributed Spark concepts, cluster behavior, and multi-node operations.

## Architecture

- **1 Master Node**: Coordinates jobs and manages the cluster
- **2 Worker Nodes**: Execute tasks and store data
- **Network**: Containers communicate over Docker network

## Setup

1. **Start the cluster:**
   ```bash
   docker-compose up -d
   ```

2. **Check cluster status:**
   ```bash
   docker-compose ps
   ```

3. **View Spark Master UI:**
   - Open http://localhost:8080 in your browser
   - You should see 2 workers registered

4. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the example script:**
   ```bash
   python example.py
   ```

## Accessing the Cluster

### From Python (Local Machine)

Connect to the cluster from your local machine:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("MyApp") \
    .master("spark://localhost:7077") \
    .config("spark.executor.memory", "1g") \
    .config("spark.executor.cores", "2") \
    .getOrCreate()
```

### From Inside Containers

You can also run Spark jobs inside the containers:

```bash
# Submit a Python job
docker exec -it spark-master spark-submit \
    --master spark://spark-master:7077 \
    /opt/bitnami/spark/scripts/example.py

# Or use PySpark shell
docker exec -it spark-master pyspark --master spark://spark-master:7077
```

## Directory Structure

```
local_multi_node/
├── docker-compose.yml    # Cluster configuration
├── requirements.txt      # Python dependencies
├── example.py           # Example script to connect to cluster
├── data/                # Mounted data directory (shared across containers)
├── notebooks/           # Jupyter notebooks (if using)
└── scripts/             # Spark scripts to run in containers
```

## Useful Commands

### Cluster Management

```bash
# Start cluster
docker-compose up -d

# Stop cluster
docker-compose down

# View logs
docker-compose logs -f spark-master
docker-compose logs -f spark-worker-1

# Restart a specific worker
docker-compose restart spark-worker-1

# Scale workers (add more)
docker-compose up -d --scale spark-worker-1=3
```

### Monitoring

- **Spark Master UI**: http://localhost:8080
- **Individual Worker UIs**: http://localhost:8081, http://localhost:8082 (if exposed)
- **Application UI**: http://localhost:4040 (when running a Spark app)

### Data Management

```bash
# Copy data into cluster
docker cp local_file.csv spark-master:/opt/bitnami/spark/data/

# Or use mounted volumes (recommended)
# Place files in ./data/ directory
```

## Learning Concepts

This setup lets you learn:

1. **Distributed Execution**: See tasks distributed across workers
2. **Shuffles**: Observe data movement between nodes
3. **Partitions**: Understand how data is partitioned across workers
4. **Spark UI**: Monitor jobs, stages, and tasks across nodes
5. **Cluster Behavior**: Test with different worker configurations

## Troubleshooting

### Workers not showing up in UI

1. Check worker logs: `docker-compose logs spark-worker-1`
2. Ensure workers can reach master: `docker exec spark-worker-1 ping spark-master`
3. Check network: `docker network ls` and `docker network inspect spark_local_multi_node_spark-network`

### Connection refused errors

- Ensure cluster is running: `docker-compose ps`
- Check master is listening: `docker exec spark-master netstat -tlnp | grep 7077`
- Verify firewall isn't blocking port 7077

### Out of memory errors

- Reduce worker memory in `docker-compose.yml`: `SPARK_WORKER_MEMORY=1g`
- Reduce executor memory in your Spark config

## Configuration

### Adjust Worker Resources

Edit `docker-compose.yml`:

```yaml
environment:
  - SPARK_WORKER_MEMORY=4g    # Increase worker memory
  - SPARK_WORKER_CORES=4      # Increase worker cores
```

### Add More Workers

Copy the `spark-worker-2` service and create `spark-worker-3`, `spark-worker-4`, etc.

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (deletes data)
docker-compose down -v

# Remove images (optional)
docker rmi bitnami/spark:3.5
```

