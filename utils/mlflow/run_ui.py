"""
Start the MLflow UI for local use (SQLite backend + file artifacts).

Hoisted from `use_cases/mlflow/run_ui.py`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


# Repo root for cwd when launching mlflow ui (utils/mlflow/run_ui.py -> parents[2])
REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    from utils.mlflow.config import (
        get_local_data_dir,
        get_mlflow_artifact_root,
        get_mlflow_tracking_uri,
    )

    tracking_uri = get_mlflow_tracking_uri()
    if tracking_uri is None:
        print(
            "MLflow UI is for local use only (Databricks uses workspace MLflow).",
            file=sys.stderr,
        )
        return 1

    artifact_root = get_mlflow_artifact_root()
    if not artifact_root:
        artifact_root = f"file://{(get_local_data_dir() / 'mlruns').resolve()}"

    get_local_data_dir().mkdir(parents=True, exist_ok=True)
    (get_local_data_dir() / "mlruns").mkdir(parents=True, exist_ok=True)

    print("MLflow UI: http://localhost:5001 (Ctrl+C to stop)")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "mlflow",
            "ui",
            "--backend-store-uri",
            tracking_uri,
            "--default-artifact-root",
            artifact_root,
            "--host",
            "0.0.0.0",
            "--port",
            "5001",
        ],
        cwd=REPO_ROOT,
    )


if __name__ == "__main__":
    sys.exit(main())

