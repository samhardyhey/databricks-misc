"""
Single entrypoint for the document intelligence use case (prescription PDFs).

Local vs Databricks:
- Local: expects prescription_pdfs/ (or DOCINT_BASE_DIR) with documents/ and labels/.
- Databricks: same Python code, with files accessible via DBFS / workspace paths
  and orchestrated via a Databricks Asset Bundle job.

Current MVP:
- Runs OCR/text extraction over PDFs (if pdfplumber installed).
+- Builds a structured "extracted fields" table directly from JSON labels or
  annotated labels.
Later iterations can plug in real NER / parsing models without changing this
entrypoint signature.
"""

from loguru import logger

from use_cases.document_intelligence.config import get_config
from use_cases.document_intelligence.data_loading import load_document_data
from use_cases.document_intelligence.ner_field_extraction import run_field_extraction
from use_cases.document_intelligence.ocr_pipeline import run_ocr


def main(config: dict | None = None) -> dict:
    """
    Run the document intelligence pipeline end-to-end.

    Returns a small summary dict for logging / diagnostics.
    """
    cfg = config or get_config()
    data_info = load_document_data(cfg)

    logger.info(
        "Document intelligence run: base_dir={}, pdfs={}, labels={}, annotated_labels={}, on_databricks={}",
        data_info["base_dir"],
        len(data_info["pdf_files"]),
        len(data_info["label_files"]),
        len(data_info["annotated_label_files"]),
        cfg["on_databricks"],
    )

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
