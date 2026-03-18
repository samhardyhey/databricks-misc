"""
Wipe the local MLflow backend and artifacts (experiments, runs, registry, model artifacts).

Uses use_cases.mlflow.config so the same paths as training/UI are removed. Safe only for
local SQLite backend; no-op on Databricks. Run: python -m use_cases.mlflow.wipe
"""

import shutil
import sys


def main() -> int:
    from use_cases.mlflow.config import get_local_data_dir, get_mlflow_tracking_uri

    if get_mlflow_tracking_uri() is None:
        print(
            "Wipe is for local MLflow only (Databricks uses workspace MLflow).",
            file=sys.stderr,
        )
        return 1

    root = get_local_data_dir()
    removed = []

    db_file = root / "mlflow.db"
    if db_file.exists():
        db_file.unlink()
        removed.append(str(db_file))
    for suffix in ("-journal", "-wal", "-shm"):
        extra = root / f"mlflow.db{suffix}"
        if extra.exists():
            extra.unlink()
            removed.append(str(extra))

    mlruns = root / "mlruns"
    if mlruns.exists():
        shutil.rmtree(mlruns)
        removed.append(str(mlruns))

    if removed:
        print("Wiped MLflow backend and artifacts:", ", ".join(removed))
    else:
        print("No local MLflow data found at", root)

    return 0


if __name__ == "__main__":
    sys.exit(main())
