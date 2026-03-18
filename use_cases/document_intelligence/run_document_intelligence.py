"""
Single entrypoint for the document intelligence use case (prescription PDFs).

- Local (DOCINT_DATA_SOURCE=local): reads documents from base_dir/documents/,
  runs OCR and field extraction, writes predictions to base_dir/predictions/.
- Remote (catalog): documents on UC volume, predictions in UC tables; use the
  DAB jobs (1_generate_data, 2_ocr_extraction, 3_field_extraction) on Databricks.
  This entrypoint is primarily for local runs.
"""

from loguru import logger

from use_cases.document_intelligence.config import get_config
from use_cases.document_intelligence.data_loading import load_document_data
from use_cases.document_intelligence.ner_field_extraction import run_field_extraction
from use_cases.document_intelligence.ocr_pipeline import run_ocr


def main(config: dict | None = None, spark=None) -> dict:
    """
    Run the document intelligence pipeline end-to-end (local only for full flow).
    When data_source is catalog, OCR/field extraction use volume/tables in the DAB jobs.
    """
    cfg = config or get_config()
    data_info = load_document_data(cfg, spark=spark)

    data_source = cfg["data_source"]
    pdf_count = len(data_info.get("pdf_files") or data_info.get("pdf_paths") or [])
    logger.info(
        "Document intelligence run: data_source={}, pdfs={}, on_databricks={}",
        data_source,
        pdf_count,
        cfg["on_databricks"],
    )

    if data_source != "local":
        logger.info(
            "Catalog path: run DAB jobs on Databricks for OCR/field extraction (volume + tables)."
        )
        return {
            "data_source": data_source,
            "ocr_count": data_info.get("ocr_count", 0),
            "fields_count": data_info.get("fields_count", 0),
        }

    ocr_df = run_ocr(cfg)
    fields_df = run_field_extraction(cfg)

    summary = {
        "n_documents": int(fields_df["doc_id"].nunique() if not fields_df.empty else 0),
        "n_ocr_docs": int(ocr_df["doc_id"].nunique() if not ocr_df.empty else 0),
        "n_ocr_rows": int(len(ocr_df)),
        "n_field_rows": int(len(fields_df)),
    }
    logger.info("Document intelligence summary: {}", summary)
    return summary


if __name__ == "__main__":
    result = main()
    logger.info("document_intelligence run done: {}", result)
