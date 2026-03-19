"""
Markdown copy for the medallion explorer: layer rationales and per-table transformation notes.

Kept separate from app.py for readability (imported from the same directory as app.py).
"""

from __future__ import annotations

# --- Full-page “chapter” per medallion layer (interactive doc) ---

LAYER_CHAPTERS: dict[str, str] = {
    "raw": """
### Raw layer — source of truth for local dbt

**Role.** This schema is **not** produced by dbt. The healthcare generator writes CSVs under
`data/local/`; `load_local_raw_to_duckdb.py` loads them into DuckDB as tables named `healthcare_*`.
Those names match **dbt sources** in `src/models/sources.yml`.

**Why keep raw separate.** We preserve the **exact landing shape** of the synthetic pipeline so
bronze can always trace back to generator output. On Databricks, the same logical role is played by
catalog raw tables from the generator job; locally, DuckDB is a stand-in.

**What you should see.** Typed columns as loaded from CSV, plus any columns the generator already
emitted. There is **no** medallion lineage metadata here yet (`_ingestion_timestamp` etc. may still
appear if the generator wrote them—bronze standardises lineage fields).
""",
    "bronze": """
### Bronze — ingest, lineage, and a thin audit wrapper

**Role.** One dbt model per source family under `src/models/bronze/`, each reading
`source('healthcare_raw', 'healthcare_*')`. Bronze is **intentionally close to raw**: same business
grain, minimal reshaping.

**Transformations we apply.**

- **Lineage & audit:** ingestion-style metadata (`_ingestion_timestamp`, `_source`, `_batch_id` where
  present from source), plus `bronze_processed_at` and `bronze_model_name` so every row records
  which bronze model materialised it.
- **Contract:** tables are materialised as **tables** in the bronze schema so downstream refs are
  stable and testable (see dbt tests on sources and referential checks).

**Rationale.** Bronze answers: *“What landed, when, and from which pipeline step?”* without baking
in business rules. That keeps reload/replay predictable and makes silver the right place for
cleaning, trimming, and flags.
""",
    "silver": """
### Silver — conformed entities, quality gates, and business semantics

**Role.** Models under `src/models/silver/` read **`ref('bronze_*')`** and emit analysis-friendly
entities: trimmed strings, rounded numbers, derived dates, **data-quality flags**, and **business
tiers** (e.g. volume/value/discount bands).

**Transformations we apply (typical patterns).**

- **Standardisation:** `trim`, `upper` on enums-like text; consistent `round` on money and rates.
- **Derived metrics:** delivery lag vs order date, expected vs actual windows, etc.
- **Quality flags:** e.g. negative quantity, invalid discount band—so bad rows are visible before we
  filter.
- **Semantic buckets:** volume tier, order value tier, delivery performance, discount tier—driven by
  `dbt_project.yml` vars such as `business_rules` thresholds.

**Rationale.** Silver is the **trusted** layer for analytics and feature pipelines: invalid rows are
**filtered out** in the model `where` clause so gold and ML code don’t repeat the same hygiene logic.
Use-case Python should prefer silver/gold over raw/bronze for modelling.
""",
    "gold": """
### Gold — analytics- and ML-ready wide tables

**Role.** Models under `src/models/gold/` join and aggregate silver (and other silver entities) into
**wide, consumption-shaped** tables: dashboards, BI, and training datasets for EBOS use-cases
(recommendations, inventory, commercial analytics).

**Transformations we apply.**

- **Aggregation:** customer-level and product-level rollups, order counts, revenue, recency, tier
  counts, etc.
- **Feature engineering:** metrics intended for ML (e.g. `gold_ml_ready_dataset`)—rolling-style
  facts, behavioural flags, scores—without pushing ML-specific logic into dbt beyond reusable
  features.
- **Curated KPIs:** pharmacy / product / supply-chain / financial summaries for reporting slices.

**Rationale.** Gold is **opinionated**: it encodes **what we want decisions to be based on** in one
place. Downstream jobs read fewer joins and stay aligned with the medallion contract in
`docs/DATA_AND_PLATFORM.md`.
""",
    "other": """
### Other schemas

**Role.** Anything not classified as raw/bronze/silver/gold for this project—e.g. default `main`,
seeds, or snapshots if you extend the project.

**Note.** The healthcare medallion dbt project primarily uses `healthcare_dev_raw` and
`healthcare_medallion_local_*` schemata; extra schemas usually come from tools or manual DB objects.
""",
}


# --- Per-table “reading guide” (optional detail when a table is selected) ---

# Fallback one-liners when no specific entry exists
_GENERIC_TABLE_BY_LAYER: dict[str, str] = {
    "raw": "**This table** is a direct load from the matching CSV in `data/local/`. Compare the same logical entity in bronze after dbt run to see lineage columns and timestamps.",
    "bronze": "**This table** mirrors a raw `healthcare_*` source with bronze lineage fields added. Expect row counts very close to raw unless the source model filters duplicates.",
    "silver": "**This table** is the cleaned, business-rule-enriched view of its bronze counterpart. Check for quality flags in the model SQL if columns look sparse—silver often filters bad rows.",
    "gold": "**This table** is purpose-built for consumption (BI or ML). Row grain may be **aggregated** (e.g. per customer or per product) rather than one row per source transaction.",
    "other": "**This table** sits outside the standard medallion classification for this app; inspect column names and schema to infer purpose.",
}

TABLE_GUIDES: dict[str, str] = {
    # Bronze — mirrors sources + lineage
    "bronze_orders": "Bronze **orders**: passthrough from `healthcare_orders` with `bronze_processed_at` / `bronze_model_name`. Use as the join spine into silver for order-level KPIs.",
    "bronze_products": "Bronze **products**: catalogue attributes from `healthcare_products`; silver rounds prices and enriches regulatory / storage labels for downstream gold features.",
    "bronze_inventory": "Bronze **inventory**: stock positions from `healthcare_inventory`; silver/gold support inventory optimisation use-cases (demand, write-off, replenishment).",
    "bronze_pharmacies": "Bronze **pharmacies**: outlet dimension from `healthcare_pharmacies`; silver standardises geography and chain flags for gold pharmacy performance.",
    "bronze_hospitals": "Bronze **hospitals**: hospital dimension; silver validates state and capacity-style fields for analytics joins.",
    "bronze_supply_chain_events": "Bronze **supply chain events**: event stream from `healthcare_supply_chain_events`; silver conformed event types and timings for gold supply-chain KPIs.",
    "bronze_expiry_batches": "Bronze **expiry batches**: batch-level expiry from generator; feeds silver risk/aging-style logic for inventory and waste stories.",
    "bronze_writeoff_events": "Bronze **write-off events**: documents disposal/write-off actions; used with inventory and demand signals in inventory use-case models.",
    "bronze_reco_interactions": "Bronze **reco interactions**: interaction facts for recommendation engine training; silver/gold shape collaborative features.",
    "bronze_reco_substitutions": "Bronze **substitutions**: substitution events for assortment / reco analytics.",
    "bronze_inventory_availability": "Bronze **inventory availability**: availability snapshots; pairs with inventory and orders for service-level style metrics.",
    "bronze_competitor_products": "Bronze **competitor products**: competitive assortment reference.",
    "bronze_competitor_price_history": "Bronze **competitor price history**: price time series for commercial / pricing analytics in gold.",
    "bronze_store_sales": "Bronze **store sales**: point-of-sale style facts for retail-facing gold tables.",
    "bronze_store_attributes": "Bronze **store attributes**: store dimension attributes for joins.",
    "bronze_promotions": "Bronze **promotions**: promotional calendar / mechanics from generator.",
    "bronze_purchase_orders": "Bronze **purchase orders**: inbound PO lines; supports replenishment and supplier stories.",
    "bronze_suppliers": "Bronze **suppliers**: vendor master from `healthcare_suppliers`.",
    "bronze_supplier_performance": "Bronze **supplier performance**: supplier KPI seeds for silver/gold sourcing metrics.",
    "bronze_warehouses": "Bronze **warehouses**: warehouse / DC dimension.",
    "bronze_warehouse_costs": "Bronze **warehouse costs**: cost facts tied to warehouse operations.",
    # Silver — cleaned entities
    "silver_orders": "Silver **orders**: trimmed enums, rounded money, **delivery lag** metrics, **quality flags** (e.g. negative qty), then **filtered** to valid rows. Adds **volume_tier**, **order_value_tier**, **delivery_performance**, **discount_tier**—see `var('business_rules')` in `dbt_project.yml`.",
    "silver_products": "Silver **products**: conformed product attributes and price bands for joins into gold product performance and ML feature tables.",
    "silver_inventory": "Silver **inventory**: cleaned stock-on-hand and movement-friendly fields; primary feed for inventory ML use-case local DuckDB paths.",
    "silver_pharmacies": "Silver **pharmacies**: outlet dimension ready for gold pharmacy rollups.",
    "silver_hospitals": "Silver **hospitals**: cleaned hospital dimension.",
    "silver_supply_chain_events": "Silver **supply chain events**: conformed event timeline for `gold_supply_chain_performance`.",
    "silver_reco_interactions": "Silver **reco interactions**: cleaned interaction grain for recommendation training base (see use-case `build_training_base` / reco pipelines).",
    "silver_reco_substitutions": "Silver **reco substitutions**: cleaned substitution grain for complementary-item style analysis.",
    # Gold — consumption
    "gold_ml_ready_dataset": "Gold **ML-ready dataset**: wide customer × product style features from `silver_orders` and `silver_products`—built for **training and batch scoring** without re-implementing SQL joins in Python. Expect aggregates and behavioural counters rather than transactional grain.",
    "gold_pharmacy_performance": "Gold **pharmacy performance**: KPIs at pharmacy grain for dashboards and commercial reviews.",
    "gold_product_performance": "Gold **product performance**: product-level sales and margin-style summaries.",
    "gold_supply_chain_performance": "Gold **supply chain performance**: KPIs derived from conformed supply-chain events.",
    "gold_financial_analytics": "Gold **financial analytics**: finance-oriented cuts (revenue, discount exposure, etc.) for leadership views.",
}


def table_reading_guide(layer_id: str, table: str, raw_schema_name: str) -> str:
    """Return markdown for the selected table, or a layer-appropriate generic line."""
    if layer_id == "raw":
        if table.startswith("healthcare_"):
            csv_stem = table.removeprefix("healthcare_")
            return (
                f"**`{table}`** is loaded verbatim from **`data/local/{csv_stem}.csv`** "
                f"(see `load_local_raw_to_duckdb.py`). In dbt this is "
                f"`source('healthcare_raw', '{table}')` in `src/models/sources.yml`."
            )
        return f"**`{table}`** in schema `{raw_schema_name}` is part of the raw landing zone."

    if table in TABLE_GUIDES:
        return f"**`{table}`** — {TABLE_GUIDES[table]}"

    return f"**`{table}`** — {_GENERIC_TABLE_BY_LAYER.get(layer_id, _GENERIC_TABLE_BY_LAYER['other'])}"
