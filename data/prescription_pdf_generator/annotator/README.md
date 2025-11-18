# Prescription PDF Annotator

Streamlit application for annotating prescription PDF documents with their corresponding JSON labels.

## Features

- **Side-by-side layout**: PDF viewer on the left, annotation form on the right
- **Form-based annotation**: Individual input fields for each JSON field
- **Navigation**:
  - Previous/Next buttons
  - Search by filename
  - List view with document thumbnails
- **Progress tracking**: Track how many documents have been reviewed
- **Review status**: Mark documents as "reviewed", "needs attention", or "pending"
- **Export functionality**: Export all annotated files as a single JSON dataset
- **Manual save**: Save annotations to a separate "annotated" directory

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.py` to set your directory paths:
```python
BASE_DIR = Path("prescription_pdfs")
DOCUMENTS_DIR = BASE_DIR / "documents"
LABELS_DIR = BASE_DIR / "labels"
ANNOTATED_DIR = BASE_DIR / "annotated"
```

## Usage

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Click "Load Documents" in the sidebar to load all matching PDF/JSON pairs

3. Navigate through documents using:
   - Previous/Next buttons
   - Search box to find specific files
   - Document list in the sidebar

4. Edit the annotation fields in the form on the right (form fields are arranged in two columns for better space utilization)

5. Click "💾 Save Annotations" to save changes to the annotated directory

6. Use the status buttons to mark documents as:
   - ✅ Reviewed
   - ⚠️ Needs Attention
   - ⚪ Pending

7. Export all annotated files using the "📦 Export Annotated Dataset" section

## Directory Structure

The app expects the following structure:
```
prescription_pdfs/
├── documents/          # PDF files
│   ├── prescription_RX123456_0001.pdf
│   └── ...
├── labels/            # Original JSON labels
│   ├── prescription_RX123456_0001.json
│   └── ...
└── annotated/         # Annotated JSON files (created by app)
    └── labels/
        ├── prescription_RX123456_0001.json
        └── ...
```

## Notes

- All form fields are currently text inputs (strings) - typing validation will be added later
- The JSON structure is preserved - only field values are changed
- Annotated files maintain the same structure as the original JSON files
