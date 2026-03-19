"""
Nominal checks: bundle layout, dashboard JSON, and app domain contract.

Avoid importing ``app/app.py`` directly (Streamlit + SDK); use AST/JSON instead.
"""

import ast
import json
from pathlib import Path


def _insights_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_dab_bundles_present() -> None:
    root = _insights_root()
    for rel in (
        "bundles/app/databricks.yml",
        "bundles/dashboards/databricks.yml",
        "bundles/genie_spaces/databricks.yml",
        "app/app.py",
    ):
        assert (root / rel).is_file(), f"missing {rel}"


def test_lakeview_dashboards_reference_bundle_variables() -> None:
    root = _insights_root()
    for name in (
        "healthcare_ops.lvdash.json",
        "animal_care_ops.lvdash.json",
        "twc_ops.lvdash.json",
    ):
        path = root / "src" / "dashboards" / name
        doc = json.loads(path.read_text())
        assert "datasets" in doc and "pages" in doc
        assert any(
            "${var.catalog}" in str(ds.get("query", "")) for ds in doc["datasets"]
        ), f"{name} should parameterize catalog via bundle var"


def test_app_defines_three_domain_specs() -> None:
    app_path = _insights_root() / "app" / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    domain_keys: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "DomainSpec":
            continue
        for kw in node.keywords:
            if kw.arg == "domain_key" and isinstance(kw.value, ast.Constant):
                domain_keys.append(str(kw.value.value))
    assert sorted(domain_keys) == sorted(
        [
            "healthcare_insights",
            "animal_care_insights",
            "twc_franchise_insights",
        ]
    )


def test_each_domain_spec_has_genie_and_dashboard_env_vars() -> None:
    app_path = _insights_root() / "app" / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    seen: dict[str, dict[str, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "DomainSpec":
            continue
        fields: dict[str, str] = {}
        for kw in node.keywords:
            if kw.arg and isinstance(kw.value, ast.Constant):
                fields[kw.arg] = str(kw.value.value)
        dk = fields.get("domain_key")
        if dk:
            seen[dk] = fields
    for key, env_names in (
        (
            "healthcare_insights",
            ("GENIE_HEALTHCARE_SPACE_ID", "HEALTHCARE_DASHBOARD_URL"),
        ),
        (
            "animal_care_insights",
            ("GENIE_ANIMAL_CARE_SPACE_ID", "ANIMAL_CARE_DASHBOARD_URL"),
        ),
        ("twc_franchise_insights", ("GENIE_TWC_SPACE_ID", "TWC_DASHBOARD_URL")),
    ):
        assert seen[key]["genie_space_env_var"] == env_names[0]
        assert seen[key]["dashboard_url_env_var"] == env_names[1]
