"""
Job-style entrypoint for prescription PDF (and labels) generation.

- Local: writes to config base_dir (documents/, labels/).
- Catalog: generates to a temp dir then uploads PDFs to UC managed volume (DOCINT_DOCUMENTS_VOLUME).
"""

import tempfile
from pathlib import Path

from loguru import logger

from data.prescription_pdf_generator.generate_prescription_pdfs_local import (
    generate_prescription_pdfs,
)
from use_cases.document_intelligence.config import get_config


def _upload_to_volume(local_documents_dir: Path, volume_path: str) -> int:
    """Upload PDFs from local dir to UC volume. Returns count uploaded. Requires Spark/dbutils on Databricks."""
    try:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()
        dbutils = DBUtils(spark)
    except Exception as e:
        logger.error("dbutils not available (run on Databricks): {}", e)
        return 0

    volume_path = volume_path.rstrip("/")
    count = 0
    for pdf_path in sorted(local_documents_dir.glob("*.pdf")):
        dest = f"{volume_path}/{pdf_path.name}"
        try:
            with pdf_path.open("rb") as f:
                dbutils.fs.put(dest, f.read(), overwrite=True)
            count += 1
            logger.debug("Uploaded {} -> {}", pdf_path.name, dest)
        except Exception as e:
            logger.error("Failed to upload {}: {}", pdf_path.name, e)
    logger.info("Uploaded {} PDFs to {}", count, volume_path)
    return count


def main() -> dict:
    cfg = get_config()
    data_source = cfg["data_source"]
    num_pdfs = cfg["generate_num_pdfs"]
    seed = cfg.get("generate_seed")

    logger.info(
        "doc-intel generate_data: data_source={}, num_pdfs={}, seed={}, on_databricks={}",
        data_source,
        num_pdfs,
        seed,
        cfg["on_databricks"],
    )

    if data_source == "catalog":
        volume_path = cfg["documents_volume_path"]
        with tempfile.TemporaryDirectory(prefix="docint_generate_") as tmp:
            output_dir = Path(tmp)
            generated = generate_prescription_pdfs(
                output_dir=output_dir,
                num_pdfs=num_pdfs,
                seed=seed,
            )
            n_uploaded = _upload_to_volume(output_dir / "documents", volume_path)
        summary = {
            "n_generated": len(generated),
            "n_uploaded": n_uploaded,
            "documents_volume_path": volume_path,
        }
    else:
        output_dir = cfg["base_dir"]
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
