# Spark Learning Environment

This directory contains two approaches for learning Spark locally:

## 📁 Directory Structure

```
spark/
├── local_single_node/     # Simple local mode (single JVM, multiple threads)
└── local_multi_node/       # Docker-based cluster (multiple containers)
```

## 🚀 Quick Start

### Option 1: Single-Node (Simplest)

Best for: Learning Spark APIs, transformations, DataFrames

```bash
cd local_single_node
pip install -r requirements.txt
python example.py
```

**Features:**
- No Docker required
- Fast iteration
- Spark UI at http://localhost:4040
- Uses all CPU cores (`local[*]`)

### Option 2: Multi-Node Cluster (Recommended for Learning)

Best for: Learning distributed concepts, cluster behavior, shuffles

```bash
cd local_multi_node
docker-compose up -d
pip install -r requirements.txt
python example.py
```

**Features:**
- Real multi-node cluster (1 master, 2 workers)
- Spark Master UI at http://localhost:8080
- Application UI at http://localhost:4040
- See tasks distributed across workers

## 📚 Learning Path

### Week 1-2: Basics
- Use `local_single_node/`
- Learn DataFrame API
- Practice transformations and actions
- Understand lazy evaluation

### Week 3-4: Distributed Concepts
- Use `local_multi_node/`
- Learn about partitions and shuffles
- Understand task distribution
- Monitor jobs in Spark UI

### Week 5+: Production
- Use Databricks Connect (already configured)
- Learn Databricks-specific features
- Work with Unity Catalog
- Practice with larger datasets

## 🔍 Key Differences

| Feature | Single-Node | Multi-Node |
|---------|------------|------------|
| Setup | Simple (pip install) | Docker required |
| Execution | Single JVM, threads | Multiple JVMs, network |
| Learning Focus | APIs, transformations | Distributed concepts |
| Spark UI | http://localhost:4040 | Master: 8080, App: 4040 |
| Best For | Development, debugging | Learning cluster behavior |

## 📖 Resources

- [Spark Documentation](https://spark.apache.org/docs/latest/)
- [PySpark API Reference](https://spark.apache.org/docs/latest/api/python/)
- [Spark SQL Guide](https://spark.apache.org/docs/latest/sql-programming-guide.html)

## 🛠️ Troubleshooting

### Single-Node Issues

**Port 4040 already in use:**
- Another Spark app is running
- Stop other Spark sessions or use different port: `.config("spark.ui.port", "4041")`

### Multi-Node Issues

**Workers not showing in UI:**
- Check logs: `docker-compose logs spark-worker-1`
- Ensure network connectivity: `docker exec spark-worker-1 ping spark-master`

**Connection refused:**
- Ensure cluster is running: `docker-compose ps`
- Check master port: `docker exec spark-master netstat -tlnp | grep 7077`

