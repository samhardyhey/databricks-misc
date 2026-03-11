"""
Configuration file for the Prescription PDF Annotator.

Edit these paths to match your directory structure.
"""

from pathlib import Path

# Base directory containing the prescription PDFs and labels
BASE_DIR = Path("prescription_pdfs")

# Directory containing PDF documents
DOCUMENTS_DIR = BASE_DIR / "documents"

# Directory containing JSON label files
LABELS_DIR = BASE_DIR / "labels"

# Directory where annotated JSON files will be saved
ANNOTATED_DIR = BASE_DIR / "annotated"
