"""
Runtime environment detection for local vs Databricks.

Use is_running_on_databricks() to fork data loading, Spark usage, etc.
"""

import os


def is_running_on_databricks() -> bool:
    """
    True when running on a Databricks cluster (notebook or job).
    False when running locally or via Databricks Connect from a local process.
    """
    return os.environ.get("DATABRICKS_RUNTIME_VERSION", "") != ""
