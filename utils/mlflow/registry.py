"""
MLflow model registry helpers.

We register each trained model with `registered_model_name=...` in the train scripts.
Best practice for deployment is to set a stable model alias (e.g. `@Champion`)
pointing to the newest version. Endpoints can then reference `models:/<name>@Champion`.
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

