"""
Streamlit app to review and verify prescription PDF predictions (annotator).

Purely for OCR/NER output: load predictions from predictions/fields/, show PDF
alongside extracted fields for verification and correction, save to annotated/labels/.
No ground-truth labels — prediction-only.
"""

import base64
import json
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
from config import ANNOTATED_DIR, DOCUMENTS_DIR, PREDICTIONS_FIELDS_DIR
from loguru import logger

# Page configuration
st.set_page_config(
    page_title="Prescription PDF Annotator — Review Predictions",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

if "review_status" not in st.session_state:
    st.session_state.review_status = {}

if "annotated_dir" not in st.session_state:
    st.session_state.annotated_dir = ANNOTATED_DIR


def load_documents(
    documents_dir: Path,
    predictions_fields_dir: Path,
) -> List[Tuple[Path, Path]]:
    """
    Load PDFs that have a corresponding prediction file (OCR/NER output).
    Returns (pdf_path, json_path) for each document with a prediction.
    """
    pdf_files = sorted(documents_dir.glob("*.pdf"))
    pairs: List[Tuple[Path, Path]] = []

    for pdf_file in pdf_files:
        pred_path = predictions_fields_dir / f"{pdf_file.stem}.json"
        if pred_path.exists():
            pairs.append((pdf_file, pred_path))
    return pairs


def load_json(file_path: Path) -> Dict:
    """Load JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def save_json(data: Dict, file_path: Path) -> None:
    """Save JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def render_form_field(label: str, value: any, key: str) -> str:
    """Render a form field based on value type."""
    if isinstance(value, dict):
        # For nested dictionaries, we'll handle them separately
        return None
    elif isinstance(value, (int, float)):
        return st.text_input(label, value=str(value), key=key)
    else:
        return st.text_input(label, value=str(value), key=key)


def render_nested_form(data: Dict, prefix: str = "") -> Dict:
    """Recursively render form fields for nested JSON structure."""
    form_data = {}

    for key, value in data.items():
        field_key = f"{prefix}_{key}" if prefix else key

        if isinstance(value, dict):
            st.subheader(key.replace("_", " ").title())
            nested_data = render_nested_form(value, field_key)
            form_data[key] = nested_data
        else:
            form_data[key] = st.text_input(
                key.replace("_", " ").title(),
                value=str(value),
                key=field_key,
            )

    return form_data


def get_review_status(file_stem: str) -> str:
    """Get review status for a file."""
    return st.session_state.review_status.get(file_stem, "pending")


def set_review_status(file_stem: str, status: str) -> None:
    """Set review status for a file."""
    st.session_state.review_status[file_stem] = status


def main():
    st.title("📋 Prescription PDF Annotator — Review Predictions")

    # Sidebar for navigation
    with st.sidebar:
        st.header("Configuration")
        st.info(
            f"📁 Documents: `{DOCUMENTS_DIR}`\n"
            f"📁 Predictions (fields): `{PREDICTIONS_FIELDS_DIR}`\n"
            f"📁 Annotated (output): `{ANNOTATED_DIR}`"
        )
        st.caption("Set DOCINT_BASE_DIR to match the pipeline base dir. Run OCR + field extraction first.")

        if st.button("Load Documents"):
            if not DOCUMENTS_DIR.exists():
                st.error(f"Documents directory not found: {DOCUMENTS_DIR}")
                return
            if not PREDICTIONS_FIELDS_DIR.exists():
                st.error(
                    "Predictions directory not found. Run the pipeline (generate → OCR → field extraction) first."
                )
                return

            pairs = load_documents(DOCUMENTS_DIR, PREDICTIONS_FIELDS_DIR)
            if pairs:
                st.session_state.document_pairs = pairs
                st.session_state.current_index = 0
                st.success(f"Loaded {len(pairs)} documents with predictions to review")
            else:
                st.warning(
                    "No PDF + prediction pairs found. Ensure predictions/fields/ contains JSON for PDFs in documents/."
                )

        # Navigation
        if "document_pairs" in st.session_state and st.session_state.document_pairs:
            st.header("Navigation")

            pairs = st.session_state.document_pairs
            total = len(pairs)

            # Progress
            reviewed_count = sum(
                1
                for status in st.session_state.review_status.values()
                if status in ["reviewed", "needs_attention"]
            )
            st.metric("Progress", f"{reviewed_count} / {total}")

            # Search
            search_term = st.text_input("Search by filename", placeholder="RX105711")
            if search_term:
                matching_indices = [
                    i
                    for i, (pdf, _) in enumerate(pairs)
                    if search_term.lower() in pdf.stem.lower()
                ]
                if matching_indices:
                    selected_index = st.selectbox(
                        "Select document",
                        options=matching_indices,
                        format_func=lambda x: pairs[x][0].stem,
                    )
                    if st.button("Go to Document"):
                        st.session_state.current_index = selected_index
                        st.rerun()

            # List view with thumbnails
            st.subheader("Document List")
            for i, (pdf, json_file) in enumerate(pairs):
                status = get_review_status(pdf.stem)
                status_icon = {
                    "pending": "⚪",
                    "reviewed": "✅",
                    "needs_attention": "⚠️",
                }.get(status, "⚪")

                if st.button(
                    f"{status_icon} {pdf.stem}",
                    key=f"nav_{i}",
                    use_container_width=True,
                ):
                    st.session_state.current_index = i
                    st.rerun()

            # Previous/Next buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "⬅️ Previous", disabled=st.session_state.current_index == 0
                ):
                    st.session_state.current_index -= 1
                    st.rerun()
            with col2:
                if st.button(
                    "Next ➡️",
                    disabled=st.session_state.current_index >= total - 1,
                ):
                    st.session_state.current_index += 1
                    st.rerun()

    # Main content area
    if "document_pairs" not in st.session_state or not st.session_state.document_pairs:
        st.info("Please configure directories and load documents in the sidebar.")
        return

    pairs = st.session_state.document_pairs
    current_index = st.session_state.current_index

    if current_index >= len(pairs):
        st.error("Invalid document index")
        return

    pdf_path, json_path = pairs[current_index]
    file_stem = pdf_path.stem

    # Load JSON: prefer last saved correction if present, else pipeline prediction
    annotated_json_path = ANNOTATED_DIR / "labels" / f"{file_stem}.json"
    try:
        if annotated_json_path.exists():
            json_data = load_json(annotated_json_path)
        else:
            json_data = load_json(json_path)
    except Exception as e:
        st.error(f"Error loading JSON: {e}")
        return

    # Side-by-side layout
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.header("📄 Document")
        st.write(f"**File:** {pdf_path.name}")
        st.caption("🔹 Verify/correct OCR + NER prediction")

        # Display PDF
        try:
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                )
                # Display PDF using iframe with base64 encoding
                base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error loading PDF: {e}")

    with col_right:
        st.header("✏️ Review / Correct Fields")

        # Review status
        current_status = get_review_status(file_stem)
        status_col1, status_col2, status_col3 = st.columns(3)
        with status_col1:
            if st.button("✅ Reviewed", use_container_width=True):
                set_review_status(file_stem, "reviewed")
                st.rerun()
        with status_col2:
            if st.button("⚠️ Needs Attention", use_container_width=True):
                set_review_status(file_stem, "needs_attention")
                st.rerun()
        with status_col3:
            if st.button("⚪ Pending", use_container_width=True):
                set_review_status(file_stem, "pending")
                st.rerun()

        st.write(f"**Status:** {current_status.replace('_', ' ').title()}")

        # Form fields
        with st.form("annotation_form"):
            # Prescription header - two columns
            st.subheader("Prescription Information")
            pres_col1, pres_col2 = st.columns(2)
            with pres_col1:
                prescription_number = st.text_input(
                    "Prescription Number",
                    value=str(json_data.get("prescription_number", "")),
                    key="prescription_number",
                )
            with pres_col2:
                prescription_date = st.text_input(
                    "Prescription Date",
                    value=str(json_data.get("prescription_date", "")),
                    key="prescription_date",
                )
            expiry_date = st.text_input(
                "Expiry Date",
                value=str(json_data.get("expiry_date", "")),
                key="expiry_date",
            )

            # Patient information - two columns
            st.subheader("Patient Information")
            pat_col1, pat_col2 = st.columns(2)
            with pat_col1:
                patient_name = st.text_input(
                    "Name",
                    value=str(json_data.get("patient", {}).get("name", "")),
                    key="patient_name",
                )
                patient_dob = st.text_input(
                    "Date of Birth",
                    value=str(json_data.get("patient", {}).get("date_of_birth", "")),
                    key="patient_dob",
                )
                patient_medicare = st.text_input(
                    "Medicare Number",
                    value=str(json_data.get("patient", {}).get("medicare_number", "")),
                    key="patient_medicare",
                )
            with pat_col2:
                patient_address = st.text_input(
                    "Address",
                    value=str(json_data.get("patient", {}).get("address", "")),
                    key="patient_address",
                )
                patient_phone = st.text_input(
                    "Phone",
                    value=str(json_data.get("patient", {}).get("phone", "")),
                    key="patient_phone",
                )

            # Doctor information - two columns
            st.subheader("Doctor Information")
            doc_col1, doc_col2 = st.columns(2)
            with doc_col1:
                doctor_name = st.text_input(
                    "Name",
                    value=str(json_data.get("doctor", {}).get("name", "")),
                    key="doctor_name",
                )
                doctor_provider = st.text_input(
                    "Provider Number",
                    value=str(json_data.get("doctor", {}).get("provider_number", "")),
                    key="doctor_provider",
                )
            with doc_col2:
                doctor_ahpra = st.text_input(
                    "AHPRA Number",
                    value=str(json_data.get("doctor", {}).get("ahpra_number", "")),
                    key="doctor_ahpra",
                )
                doctor_signature_date = st.text_input(
                    "Signature Date",
                    value=str(json_data.get("doctor", {}).get("signature_date", "")),
                    key="doctor_signature_date",
                )

            # Facility information - two columns
            st.subheader("Facility Information")
            fac_col1, fac_col2 = st.columns(2)
            with fac_col1:
                facility_name = st.text_input(
                    "Name",
                    value=str(json_data.get("facility", {}).get("name", "")),
                    key="facility_name",
                )
                facility_address = st.text_input(
                    "Address",
                    value=str(json_data.get("facility", {}).get("address", "")),
                    key="facility_address",
                )
            with fac_col2:
                facility_phone = st.text_input(
                    "Phone",
                    value=str(json_data.get("facility", {}).get("phone", "")),
                    key="facility_phone",
                )
                facility_abn = st.text_input(
                    "ABN",
                    value=str(json_data.get("facility", {}).get("abn", "")),
                    key="facility_abn",
                )

            # Medication information - two columns
            st.subheader("Medication Information")
            med_col1, med_col2 = st.columns(2)
            with med_col1:
                medication_name = st.text_input(
                    "Name",
                    value=str(json_data.get("medication", {}).get("name", "")),
                    key="medication_name",
                )
                medication_dosage_form = st.text_input(
                    "Dosage Form",
                    value=str(json_data.get("medication", {}).get("dosage_form", "")),
                    key="medication_dosage_form",
                )
                medication_strength = st.text_input(
                    "Strength",
                    value=str(json_data.get("medication", {}).get("strength", "")),
                    key="medication_strength",
                )
                medication_quantity = st.text_input(
                    "Quantity",
                    value=str(json_data.get("medication", {}).get("quantity", "")),
                    key="medication_quantity",
                )
            with med_col2:
                medication_frequency = st.text_input(
                    "Frequency",
                    value=str(json_data.get("medication", {}).get("frequency", "")),
                    key="medication_frequency",
                )
                medication_duration = st.text_input(
                    "Duration",
                    value=str(json_data.get("medication", {}).get("duration", "")),
                    key="medication_duration",
                )
                medication_instructions = st.text_input(
                    "Instructions",
                    value=str(json_data.get("medication", {}).get("instructions", "")),
                    key="medication_instructions",
                )
                medication_repeats = st.text_input(
                    "Repeats",
                    value=str(json_data.get("medication", {}).get("repeats", "")),
                    key="medication_repeats",
                )

            # Save button
            if st.form_submit_button("💾 Save Annotations", use_container_width=True):
                # Reconstruct JSON structure
                updated_data = {
                    "prescription_number": prescription_number,
                    "prescription_date": prescription_date,
                    "expiry_date": expiry_date,
                    "patient": {
                        "name": patient_name,
                        "date_of_birth": patient_dob,
                        "address": patient_address,
                        "medicare_number": patient_medicare,
                        "phone": patient_phone,
                    },
                    "doctor": {
                        "name": doctor_name,
                        "provider_number": doctor_provider,
                        "ahpra_number": doctor_ahpra,
                        "signature_date": doctor_signature_date,
                    },
                    "facility": {
                        "name": facility_name,
                        "address": facility_address,
                        "phone": facility_phone,
                        "abn": facility_abn,
                    },
                    "medication": {
                        "name": medication_name,
                        "dosage_form": medication_dosage_form,
                        "strength": medication_strength,
                        "quantity": medication_quantity,
                        "frequency": medication_frequency,
                        "duration": medication_duration,
                        "instructions": medication_instructions,
                        "repeats": medication_repeats,
                    },
                }

                # Save to annotated directory
                save_json(updated_data, annotated_json_path)
                st.success(f"✅ Saved annotations to {annotated_json_path}")
                logger.info(f"Saved annotations for {file_stem}")

    # Export functionality
    st.divider()
    with st.expander("📦 Export Annotated Dataset"):
        if st.button("Export All Annotated Files"):
            if not ANNOTATED_DIR.exists():
                st.warning("No annotated directory found")
            else:
                annotated_labels_dir = ANNOTATED_DIR / "labels"
                if annotated_labels_dir.exists():
                    json_files = list(annotated_labels_dir.glob("*.json"))
                    if json_files:
                        # Create export package
                        export_data = {
                            "total_files": len(json_files),
                            "files": {},
                        }
                        for json_file in json_files:
                            export_data["files"][json_file.stem] = load_json(json_file)

                        export_json = json.dumps(export_data, indent=2)
                        st.download_button(
                            label="📥 Download Export JSON",
                            data=export_json,
                            file_name="annotated_dataset.json",
                            mime="application/json",
                        )
                        st.success(f"Ready to export {len(json_files)} annotated files")
                    else:
                        st.info("No annotated files found")
                else:
                    st.info("No annotated labels directory found")


if __name__ == "__main__":
    main()
