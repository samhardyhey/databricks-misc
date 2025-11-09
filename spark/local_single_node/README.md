# Local Single-Node Spark Setup

This setup runs Spark in local mode on your machine - perfect for learning Spark APIs, transformations, and DataFrames without the complexity of a cluster.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the example script:**
   ```bash
   python example.py
   ```

3. **Or use in a Jupyter notebook:**
   ```bash
   jupyter notebook
   ```

## How It Works

- **Master**: `local[*]` - Uses all CPU cores on your machine
- **Workers**: Threads within the same JVM process
- **Storage**: Local filesystem
- **Network**: No network overhead (all in-process)

## Use Cases

- Learning Spark DataFrame API
- Testing transformations and actions
- Developing and debugging Spark code
- Working with small to medium datasets (< 10GB)

## Limitations

- Not a real distributed cluster
- Limited to single machine resources
- No network communication between nodes
- Can't test cluster-specific features (e.g., node failures)

## Spark UI

When you run a Spark application, the UI is available at:
- **URL**: http://localhost:4040
- **Auto-starts**: When SparkContext is created
- **Auto-stops**: When SparkContext is stopped

