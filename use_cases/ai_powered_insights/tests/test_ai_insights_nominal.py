"""
Nominal checks: bundle layout and docs (no heavy app imports).
"""

from pathlib import Path


def test_dab_bundles_present() -> None:
    root = Path(__file__).resolve().parents[1]
    for rel in (
        "bundles/app/databricks.yml",
        "bundles/dashboards/databricks.yml",
        "bundles/genie_spaces/databricks.yml",
        "app/app.py",
    ):
        assert (root / rel).is_file(), f"missing {rel}"
