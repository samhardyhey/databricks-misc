"""
Local medallion viewer: browse DuckDB tables produced by CSV load + dbt (bronze/silver/gold).

Run from repo root: make data-local-medallion-app-run
(needs data/local/medallion.duckdb — e.g. make data-local-dbt-run first)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

import duckdb
import narratives
import pandas as pd
import streamlit as st
from loguru import logger

# Tab key and label (long-form copy lives in narratives.LAYER_CHAPTERS)
LAYER_TABS: tuple[tuple[str, str], ...] = (
    ("raw", "0 · Raw (CSV load)"),
    ("bronze", "1 · Bronze (dbt)"),
    ("silver", "2 · Silver (dbt)"),
    ("gold", "3 · Gold (dbt)"),
    ("other", "Other schemas"),
)


def default_duckdb_path() -> Path:
    env = os.environ.get("DBT_DUCKDB_PATH", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "local" / "medallion.duckdb"


def connect_readonly(path: Path) -> duckdb.DuckDBPyConnection:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return duckdb.connect(str(path), read_only=True)


def list_schemas(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute(
        """
        SELECT DISTINCT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
        ORDER BY 1
        """
    ).fetchall()
    return [r[0] for r in rows]


def layer_key_for_schema(schema: str, fixed_raw: str) -> str:
    if schema == fixed_raw:
        return "raw"
    if schema.endswith("_bronze"):
        return "bronze"
    if schema.endswith("_silver"):
        return "silver"
    if schema.endswith("_gold"):
        return "gold"
    return "other"


def list_tables(con: duckdb.DuckDBPyConnection, schema: str) -> list[str]:
    rows = con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = ?
          AND table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY table_name
        """,
        [schema],
    ).fetchall()
    return [r[0] for r in rows]


def table_row_count(con: duckdb.DuckDBPyConnection, schema: str, table: str) -> int:
    q = f'SELECT COUNT(*) AS c FROM "{schema}"."{table}"'
    return int(con.execute(q).fetchone()[0])


@st.cache_data(ttl=30, show_spinner=False)
def preview_table(
    db_path_str: str, schema: str, table: str, limit: int
) -> pd.DataFrame:
    path = Path(db_path_str)
    lim = int(limit)
    con = connect_readonly(path)
    try:
        q = f'SELECT * FROM "{schema}"."{table}" LIMIT ?'
        return con.execute(q, [lim]).df()
    finally:
        con.close()


def schemas_for_layer(
    all_schemas: Sequence[str], layer_id: str, fixed_raw: str
) -> list[str]:
    if layer_id == "raw":
        return [s for s in all_schemas if s == fixed_raw]
    if layer_id == "other":
        keys = {"raw", "bronze", "silver", "gold"}
        return [
            s
            for s in all_schemas
            if layer_key_for_schema(s, fixed_raw) not in keys
        ]
    return [s for s in all_schemas if layer_key_for_schema(s, fixed_raw) == layer_id]


def main() -> None:
    st.set_page_config(
        page_title="Healthcare medallion (local DuckDB)",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("Healthcare medallion — interactive walkthrough")
    st.caption(
        "Each tab is a **chapter**: rationale for that layer. Pick a table for a **reading guide**, "
        "then inspect rows below."
    )

    with st.sidebar:
        st.subheader("Connection")
        default_p = default_duckdb_path()
        path_input = st.text_input(
            "DuckDB file path",
            value=str(default_p),
            help="Defaults from DBT_DUCKDB_PATH or data/local/medallion.duckdb",
        )
        limit = st.slider("Preview row limit", min_value=10, max_value=2000, value=200, step=10)
        st.markdown(
            "Need a database? From repo root: `make data-local-dbt-run` "
            "(or full `make data-local-e2e`)."
        )

    db_path = Path(path_input).expanduser().resolve()
    if not db_path.is_file():
        st.error(f"DuckDB file not found: `{db_path}`")
        st.stop()

    try:
        con = connect_readonly(db_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("DuckDB connect failed: {}", exc)
        st.error(f"Could not open DuckDB (is another process locking it?): {exc}")
        st.stop()

    try:
        all_schemas = list_schemas(con)
    finally:
        con.close()

    if not all_schemas:
        st.warning("No user schemas in this database.")
        st.stop()

    raw_name = "healthcare_dev_raw"
    if raw_name not in all_schemas:
        raw_name = next(
            (s for s in all_schemas if "raw" in s.lower() and s.startswith("healthcare_")),
            all_schemas[0],
        )

    with st.expander("End-to-end pipeline (diagram)", expanded=False):
        st.markdown(
            """
```text
data/local/*.csv
    │  make data-local-generate
    ▼
load_local_raw_to_duckdb.py
    │  schema: healthcare_dev_raw  (tables healthcare_*)
    ▼
dbt run (profile duckdb, path from DBT_DUCKDB_PATH)
    │  bronze  →  *_bronze   (lineage, audit)
    │  silver  →  *_silver   (cleaning, tiers, filters)
    ▼  gold    →  *_gold     (KPIs, ML-wide features)
use-case Python (reco / inventory / …) reads gold & silver
```
"""
        )

    tab_labels = [label for (_, label) in LAYER_TABS]
    tabs = st.tabs(tab_labels)

    for tab, (layer_id, _label) in zip(tabs, LAYER_TABS, strict=True):
        with tab:
            st.markdown(narratives.LAYER_CHAPTERS.get(layer_id, ""))

            layer_schemas = schemas_for_layer(all_schemas, layer_id, raw_name)
            if not layer_schemas:
                st.info("No schemas in this layer for the current database.")
                continue

            schema_pick = st.selectbox(
                "Schema",
                layer_schemas,
                key=f"schema_{layer_id}",
            )
            con2 = connect_readonly(db_path)
            try:
                tables = list_tables(con2, schema_pick)
            finally:
                con2.close()

            if not tables:
                st.warning(f"No tables in `{schema_pick}`.")
                continue

            table_pick = st.selectbox(
                "Table",
                tables,
                key=f"table_{layer_id}_{schema_pick}",
            )

            st.markdown("#### This table")
            with st.container(border=True):
                st.markdown(narratives.table_reading_guide(layer_id, table_pick, raw_name))

            con3 = connect_readonly(db_path)
            try:
                nrows = table_row_count(con3, schema_pick, table_pick)
            except Exception as exc:  # noqa: BLE001
                logger.warning("row count failed: {}", exc)
                nrows = -1
            finally:
                con3.close()

            c1, c2, c3 = st.columns(3)
            c1.metric("Rows (full table)", f"{nrows:,}" if nrows >= 0 else "n/a")
            try:
                df_head = preview_table(str(db_path), schema_pick, table_pick, limit)
                c2.metric("Columns", len(df_head.columns))
                c3.metric("Preview rows", min(limit, nrows) if nrows >= 0 else limit)
                st.dataframe(df_head, width="stretch", hide_index=True)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Preview failed: {exc}")
                logger.exception("preview failed")


if __name__ == "__main__":
    main()
