import argparse
import json
import random
import shutil
from pathlib import Path
from typing import List

from faker import Faker
from loguru import logger

from data.prescription_pdf_generator.prescription_pdf_generator import (
    create_prescription_pdf, generate_prescription_data)


def generate_prescription_pdfs(
    output_dir: Path, num_pdfs: int, seed: int = None
) -> List[Path]:
    """Generate N prescription PDF files with corresponding JSON labels."""
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    fake = Faker("en_AU")  # Australian locale for realistic data

    # Create documents and labels subdirectories
    documents_dir = output_dir / "documents"
    labels_dir = output_dir / "labels"

    # Delete output directory if it exists, then create fresh
    if output_dir.exists():
        logger.info(f"Removing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)

    documents_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []

    logger.info(f"Generating {num_pdfs} prescription PDF files...")

    for i in range(1, num_pdfs + 1):
        # Generate prescription data
        prescription_data = generate_prescription_data(fake)

        # Create base filename (without extension)
        base_filename = (
            f"prescription_{prescription_data['prescription_number']}_{i:04d}"
        )

        # Create PDF path
        pdf_path = documents_dir / f"{base_filename}.pdf"

        # Create JSON label path
        json_path = labels_dir / f"{base_filename}.json"

        # Create PDF
        try:
            create_prescription_pdf(pdf_path, prescription_data)

            # Save JSON label file with the prescription data
            with open(json_path, "w") as f:
                json.dump(prescription_data, f, indent=2)

            generated_files.append(pdf_path)
            logger.debug(f"Generated: {base_filename}.pdf and {base_filename}.json")
        except Exception as e:
            logger.error(f"Failed to generate {base_filename}: {e}")

    logger.info(
        f"Successfully generated {len(generated_files)} PDF files in {documents_dir} and {len(generated_files)} JSON labels in {labels_dir}"
    )
    return generated_files


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate mock prescription PDF files for document intelligence testing"
    )
    parser.add_argument(
        "-n",
        "--num-pdfs",
        type=int,
        default=10,
        help="Number of PDF files to generate (default: 10)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="prescription_pdfs",
        help="Output directory for PDF files (default: prescription_pdfs)",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible generation (optional)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    logger.info(f"Starting prescription PDF generation...")
    logger.info(f"Output directory: {output_dir.absolute()}")
    logger.info(f"Number of PDFs: {args.num_pdfs}")

    generated_files = generate_prescription_pdfs(
        output_dir=output_dir,
        num_pdfs=args.num_pdfs,
        seed=args.seed,
    )

    logger.success(f"Completed! Generated {len(generated_files)} PDF files.")


if __name__ == "__main__":
    main()
