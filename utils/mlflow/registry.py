"""
MLflow model registry helpers.

We register each trained model with ``registered_model_name=...`` in the train scripts.
Best practice for deployment is to set a stable model alias (e.g. ``@Champion``)
on the **latest** registered version after each successful training run. Batch jobs and
``predict.py`` entrypoints should default to ``models:/<name>@Champion`` (overridable via env).

**Hard experiments in this repo (use Champion consistently):**

- **Recommendation:** item_similarity, ALS, LightFM, ranker — train scripts call
  ``set_latest_version_alias(..., alias="Champion")``; apply bundles set ``*_MODEL_URI``
  to ``models:/recommendation_engine-<model>@Champion`` by default.
- **Inventory:** write-off classifier — ``inventory_optimization-writeoff_risk@Champion``;
  set ``WRITEOFF_RISK_MODEL_URI`` in apply jobs. Demand forecasting is not registry-backed
  (baseline / MLflow metrics only until a logged model exists).
"""

from __future__ import annotations

from mlflow.tracking import MlflowClient


def set_latest_version_alias(
    registered_model_name: str, alias: str = "Champion"
) -> None:
    """
    Point `alias` (e.g. @Champion) at the latest version of `registered_model_name`.

    No-op if the model has no versions yet.
    """
    client = MlflowClient()
    versions = client.search_model_versions(
        f"name = '{registered_model_name}'", max_results=50
    )
    if not versions:
        return

    latest = max(versions, key=lambda mv: int(mv.version))
    client.set_registered_model_alias(
        name=registered_model_name, alias=alias, version=latest.version
    )

