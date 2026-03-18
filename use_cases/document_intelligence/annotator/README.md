# Prescription PDF Annotator — Review Predictions

Streamlit app to **verify and correct OCR + NER predictions** for prescription PDFs. Prediction-only: it loads from `predictions/fields/` (pipeline output) and saves corrections to `annotated/labels/`. No ground-truth labels are used.

## Role in the pipeline

1. **Pipeline** generates documents (PDFs), runs OCR + field extraction, and writes predictions to `predictions/fields/`.
2. **This app** loads those predictions, shows PDF alongside extracted fields for human verification/correction, and saves corrected JSON to `annotated/labels/`.
3. Corrected data can feed evaluation and optional NER training; approved records can trigger downstream systems.

## Features

- **Prediction-only**: Reads only from `predictions/fields/` (OCR/NER output). No labels.
- **Side-by-side**: PDF on the left, editable fields on the right.
- **Save corrections** to `annotated/labels/` (same nested JSON schema).
- **Navigation**: Previous/Next, search by filename, list with review status.
- **Export**: Export all annotated files as a single JSON dataset.

## Configuration

Use the **same base dir** as the pipeline:

- **DOCINT_BASE_DIR** or **LOCAL_DATA_PATH**: Base directory. Default: repo root `prescription_pdfs/`.

Paths under base dir:

- `documents/` — PDFs
- `predictions/fields/` — Pipeline predictions (only source for review)
- `annotated/labels/` — Corrected output (written by this app)

## Usage

1. **Run the pipeline** (generate → OCR → field extraction) so that `predictions/fields/` is populated.

2. Start the app:
   ```bash
   DOCINT_BASE_DIR=prescription_pdfs streamlit run use_cases/document_intelligence/annotator/app.py
   ```
   Or from the annotator directory:
   ```bash
   cd use_cases/document_intelligence/annotator
   streamlit run app.py
   ```

3. Click **Load Documents**. The app loads only PDFs that have a matching prediction file.

4. Verify/correct fields and click **Save Annotations**. Use status buttons to mark Reviewed / Needs attention / Pending.

5. Optionally **Export Annotated Dataset** to download all corrected JSONs.

## Directory structure

```
<DOCINT_BASE_DIR>/
├── documents/           # PDFs
├── predictions/
│   └── fields/          # Pipeline predictions (only source)
└── annotated/
    └── labels/          # Corrected output (written by this app)
```

## Notes

- No labels are read or generated; this app is purely for annotating/verifying predictions from OCR/NER.
- JSON in `predictions/fields/` must use the nested schema (patient, doctor, facility, medication) expected by the form.
