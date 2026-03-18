"""
Job-style entrypoint for prescription PDF (and labels) generation.

Intended for:
- Local runs: python use_cases/document_intelligence/jobs/1_generate_data.py
- Databricks jobs: spark_python_task.python_file pointing here.

Uses config base_dir as output root; creates documents/ and labels/ underneath.
"""

from loguru import logger

from data.prescription_pdf_generator.generate_prescription_pdfs_local import (
    generate_prescription_pdfs,
)
from use_cases.document_intelligence.config import get_config


def main() -> dict:
    cfg = get_config()
    output_dir = cfg["base_dir"]
    num_pdfs = cfg["generate_num_pdfs"]
    seed = cfg.get("generate_seed")

    logger.info(
        "doc-intel generate_data: output_dir={}, num_pdfs={}, seed={}, on_databricks={}",
        output_dir,
        num_pdfs,
        seed,
        cfg["on_databricks"],
    )

    generated = generate_prescription_pdfs(
        output_dir=output_dir,
        num_pdfs=num_pdfs,
        seed=seed,
    )

    summary = {
        "n_generated": len(generated),
        "output_dir": str(output_dir),
    }
    logger.info("doc-intel generate_data summary: {}", summary)
    return summary


if __name__ == "__main__":
    result = main()
    logger.info("doc-intel generate_data run done: {}", result)
