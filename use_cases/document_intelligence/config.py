"""
Document intelligence config: local file paths vs remote (UC volume + tables).

Same pattern as inventory_optimization / recommendation_engine:
- DOCINT_DATA_SOURCE: local | catalog | auto (auto = catalog on Databricks, else local).
- Local: DOCINT_BASE_DIR holds documents/, predictions/ (ocr/, fields/), annotated/.
- Remote: documents on UC managed volume; predictions in Unity Catalog tables.
"""

import os
from pathlib import Path
from typing import Literal

from utils.env_utils import is_running_on_databricks
from utils.use_case_utils import get_catalog_schema as _shared_catalog_schema
from utils.use_case_utils import get_env_str, resolve_data_source, resolve_local_base_dir

_DEFAULT_LOCAL_BASE_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "local" / "prescription_pdfs"
)
_DEFAULT_CATALOG_SCHEMA = "workspace.document_intelligence_dev"
_DEFAULT_DOCUMENTS_VOLUME_PATH = (
    "/Volumes/workspace/document_intelligence_dev/prescription_documents"
)

DataSource = Literal["local", "catalog", "auto"]


def get_data_source() -> Literal["local", "catalog"]:
    """
    Resolved data source: 'local' (files) or 'catalog' (UC volume + tables).
    DOCINT_DATA_SOURCE: 'local' | 'catalog' | 'auto'.
    - 'auto': use 'catalog' on Databricks, else 'local'.
    """
    return resolve_data_source(env_var_name="DOCINT_DATA_SOURCE")


def get_local_base_dir() -> Path:
    """
    Base directory for local runs: documents/, predictions/, annotated/.
    Override with DOCINT_BASE_DIR or LOCAL_DATA_PATH.
    """
    return resolve_local_base_dir(
        primary_env="DOCINT_BASE_DIR",
        default_path=_DEFAULT_LOCAL_BASE_DIR,
    )


def get_catalog_schema() -> str:
    """Unity Catalog schema for document intelligence tables. Override with DOCINT_CATALOG_SCHEMA."""
    return _shared_catalog_schema(
        env_var_name="DOCINT_CATALOG_SCHEMA",
        default=_DEFAULT_CATALOG_SCHEMA,
    )


def get_documents_volume_path() -> str:
    """
    UC managed volume path for prescription PDFs (remote only).
    Override with DOCINT_DOCUMENTS_VOLUME.
    """
    return get_env_str(
        "DOCINT_DOCUMENTS_VOLUME", _DEFAULT_DOCUMENTS_VOLUME_PATH
    ).rstrip("/")


def get_table_doc_pages() -> str:
    """Table name for OCR output (e.g. silver_doc_pages). Override with DOCINT_TABLE_DOC_PAGES."""
    return get_env_str("DOCINT_TABLE_DOC_PAGES", "silver_doc_pages")


def get_table_doc_fields_extracted() -> str:
    """Table name for field extraction output. Override with DOCINT_TABLE_DOC_FIELDS."""
    return get_env_str("DOCINT_TABLE_DOC_FIELDS", "silver_doc_fields_extracted")


def get_generate_num_pdfs() -> int:
    """Number of prescription PDFs to generate. Override with DOCINT_NUM_PDFS."""
    raw = os.environ.get("DOCINT_NUM_PDFS", "10").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 10


def get_generate_seed() -> int | None:
    """Random seed for reproducible generation. Override with DOCINT_SEED (empty = None)."""
    raw = os.environ.get("DOCINT_SEED", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def get_config() -> dict:
    """
    Single config dict for the document intelligence pipeline.
    - data_source: 'local' | 'catalog'
    - base_dir: Path (local only)
    - documents_dir: Path (local) or use documents_volume_path (catalog)
    - predictions_dir: Path (local only)
    - labels_dir, annotated_dir: Path (local only)
    - catalog_schema: str (catalog only)
    - documents_volume_path: str (catalog only)
    - table_doc_pages, table_doc_fields_extracted: str (catalog only)
    - on_databricks: bool
    - generate_num_pdfs, generate_seed: for generate job
    """
    data_source = get_data_source()
    base_dir = get_local_base_dir()
    return {
        "data_source": data_source,
        "base_dir": base_dir,
        "documents_dir": base_dir / "documents",
        "predictions_dir": base_dir / "predictions",
        "labels_dir": base_dir / "labels",
        "annotated_dir": base_dir / "annotated",
        "catalog_schema": get_catalog_schema(),
        "documents_volume_path": get_documents_volume_path(),
        "table_doc_pages": get_table_doc_pages(),
        "table_doc_fields_extracted": get_table_doc_fields_extracted(),
        "on_databricks": is_running_on_databricks(),
        "generate_num_pdfs": get_generate_num_pdfs(),
        "generate_seed": get_generate_seed(),
    }
