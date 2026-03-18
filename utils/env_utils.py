"""
Runtime environment detection for local vs Databricks.

This was previously located at `use_cases/env_utils.py` but is hoisted to the
root `utils/` module so all use-cases share a single import location.
"""

from __future__ import annotations

import os


def is_running_on_databricks() -> bool:
    """
    True when running on a Databricks cluster (notebook or job).
    False when running locally or via Databricks Connect from a local process.
    """

    return os.environ.get("DATABRICKS_RUNTIME_VERSION", "") != ""

