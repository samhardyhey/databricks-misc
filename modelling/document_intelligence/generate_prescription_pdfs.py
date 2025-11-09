"""
Generate mock prescription PDF files for document intelligence testing.

This script creates N-number of PDF files containing realistic prescription
information including patient details, hospital/clinic info, doctor information,
medication details, dosage, frequency, and other prescription fields.
"""

import argparse
import random
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List

from faker import Faker
from loguru import logger
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# Common Australian medications
COMMON_MEDICATIONS = [
    "Paracetamol 500mg",
    "Ibuprofen 400mg",
    "Amoxicillin 500mg",
    "Metformin 500mg",
    "Atorvastatin 20mg",
    "Ramipril 5mg",
    "Amlodipine 5mg",
    "Omeprazole 20mg",
    "Sertraline 50mg",
    "Amlodipine 10mg",
    "Salbutamol 100mcg",
    "Fluticasone 50mcg",
    "Levothyroxine 50mcg",
    "Warfarin 5mg",
    "Aspirin 100mg",
    "Clopidogrel 75mg",
    "Furosemide 40mg",
    "Bisoprolol 5mg",
    "Losartan 50mg",
    "Pantoprazole 40mg",
]

DOSAGE_FORMS = ["Tablet", "Capsule", "Injection", "Cream", "Ointment", "Syrup", "Inhaler", "Drops"]

FREQUENCIES = [
    "Once daily",
    "Twice daily",
    "Three times daily",
    "Four times daily",
    "Every 6 hours",
    "Every 8 hours",
    "Every 12 hours",
    "As needed",
    "Before meals",
    "After meals",
    "With food",
]

DURATIONS = [
    "7 days",
    "10 days",
    "14 days",
    "21 days",
    "28 days",
    "30 days",
    "60 days",
    "90 days",
    "Ongoing",
    "As directed",
]


def generate_prescription_data(fake: Faker) -> Dict:
    """Generate mock prescription data using Faker."""
    prescription_date = fake.date_between(start_date="-1y", end_date="today")
    expiry_date = prescription_date + timedelta(days=random.choice([180, 365]))

    medication = random.choice(COMMON_MEDICATIONS)
    dosage_form = random.choice(DOSAGE_FORMS)
    frequency = random.choice(FREQUENCIES)
    duration = random.choice(DURATIONS)
    quantity = random.choice([10, 20, 30, 50, 60, 90, 100, 120])

    # Generate patient details
    patient_data = {
        "name": fake.name(),
        "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%d/%m/%Y"),
        "address": fake.address().replace("\n", ", "),
        "medicare_number": f"{random.randint(2,9)}{random.randint(100000000, 999999999)}",
        "phone": fake.phone_number(),
    }

    # Generate doctor details
    doctor_data = {
        "name": f"Dr. {fake.first_name()} {fake.last_name()}",
        "provider_number": f"{random.randint(100000, 999999)}",
        "ahpra_number": f"MED{random.randint(1000000, 9999999)}",
        "signature_date": prescription_date.strftime("%d/%m/%Y"),
    }

    # Generate hospital/clinic details
    facility_data = {
        "name": random.choice([
            fake.company() + " Hospital",
            fake.company() + " Medical Centre",
            fake.company() + " Clinic",
            fake.company() + " Health",
        ]),
        "address": fake.address().replace("\n", ", "),
        "phone": fake.phone_number(),
        "abn": f"{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)}",
    }

    # Generate medication details
    medication_data = {
        "name": medication,
        "dosage_form": dosage_form,
        "strength": medication.split()[-1] if len(medication.split()) > 1 else "N/A",
        "quantity": quantity,
        "frequency": frequency,
        "duration": duration,
        "instructions": fake.sentence(nb_words=random.randint(5, 12)).replace(".", ""),
        "repeats": random.choice([0, 1, 2, 3, 4, 5]),
    }

    return {
        "prescription_number": f"RX{random.randint(100000, 999999)}",
        "prescription_date": prescription_date.strftime("%d/%m/%Y"),
        "expiry_date": expiry_date.strftime("%d/%m/%Y"),
        "patient": patient_data,
        "doctor": doctor_data,
        "facility": facility_data,
        "medication": medication_data,
    }


def create_prescription_pdf(output_path: Path, prescription_data: Dict) -> None:
    """Create a PDF file with prescription information."""
    doc = SimpleDocTemplate(str(output_path), pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1a5490"),
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#2c5aa0"),
        spaceAfter=6,
    )

    # Title
    story.append(Paragraph("PRESCRIPTION", title_style))
    story.append(Spacer(1, 0.5 * cm))

    # Prescription header info
    header_data = [
        ["Prescription Number:", prescription_data["prescription_number"]],
        ["Date:", prescription_data["prescription_date"]],
        ["Valid Until:", prescription_data["expiry_date"]],
    ]
    header_table = Table(header_data, colWidths=[5 * cm, 10 * cm])
    header_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 0.5 * cm))

    # Patient Information
    story.append(Paragraph("PATIENT INFORMATION", heading_style))
    patient_data = prescription_data["patient"]
    patient_info = [
        ["Name:", patient_data["name"]],
        ["Date of Birth:", patient_data["date_of_birth"]],
        ["Address:", patient_data["address"]],
        ["Medicare Number:", patient_data["medicare_number"]],
        ["Phone:", patient_data["phone"]],
    ]
    for label, value in patient_info:
        story.append(Paragraph(f"<b>{label}</b> {value}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))

    # Prescribing Doctor Information
    story.append(Paragraph("PRESCRIBING DOCTOR", heading_style))
    doctor_data = prescription_data["doctor"]
    doctor_info = [
        ["Name:", doctor_data["name"]],
        ["Provider Number:", doctor_data["provider_number"]],
        ["AHPRA Number:", doctor_data["ahpra_number"]],
        ["Date:", doctor_data["signature_date"]],
    ]
    for label, value in doctor_info:
        story.append(Paragraph(f"<b>{label}</b> {value}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))

    # Facility Information
    story.append(Paragraph("FACILITY INFORMATION", heading_style))
    facility_data = prescription_data["facility"]
    facility_info = [
        ["Name:", facility_data["name"]],
        ["Address:", facility_data["address"]],
        ["Phone:", facility_data["phone"]],
        ["ABN:", facility_data["abn"]],
    ]
    for label, value in facility_info:
        story.append(Paragraph(f"<b>{label}</b> {value}", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    # Medication Information
    story.append(Paragraph("MEDICATION", heading_style))
    med_data = prescription_data["medication"]

    # Create table data with Paragraph objects for text wrapping
    medication_table_data = [
        [
            Paragraph("<b>Medication Name:</b>", styles["Normal"]),
            Paragraph(med_data["name"], styles["Normal"]),
        ],
        [
            Paragraph("<b>Dosage Form:</b>", styles["Normal"]),
            Paragraph(med_data["dosage_form"], styles["Normal"]),
        ],
        [
            Paragraph("<b>Strength:</b>", styles["Normal"]),
            Paragraph(med_data["strength"], styles["Normal"]),
        ],
        [
            Paragraph("<b>Quantity:</b>", styles["Normal"]),
            Paragraph(str(med_data["quantity"]), styles["Normal"]),
        ],
        [
            Paragraph("<b>Frequency:</b>", styles["Normal"]),
            Paragraph(med_data["frequency"], styles["Normal"]),
        ],
        [
            Paragraph("<b>Duration:</b>", styles["Normal"]),
            Paragraph(med_data["duration"], styles["Normal"]),
        ],
        [
            Paragraph("<b>Repeats:</b>", styles["Normal"]),
            Paragraph(str(med_data["repeats"]), styles["Normal"]),
        ],
        [
            Paragraph("<b>Instructions:</b>", styles["Normal"]),
            Paragraph(med_data["instructions"], styles["Normal"]),
        ],
    ]

    # Adjust column widths to better fit content and allow wrapping
    # Using Paragraph objects enables automatic text wrapping
    medication_table = Table(medication_table_data, colWidths=[4.5 * cm, 10.5 * cm])
    medication_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(medication_table)
    story.append(Spacer(1, 0.5 * cm))

    # Footer
    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            "<i>This is a mock prescription generated for testing purposes only.</i>",
            styles["Normal"],
        )
    )

    # Build PDF
    doc.build(story)


def generate_prescription_pdfs(
    output_dir: Path, num_pdfs: int, seed: int = None
) -> List[Path]:
    """Generate N prescription PDF files."""
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    fake = Faker("en_AU")  # Australian locale for realistic data

    # Delete output directory if it exists, then create fresh
    if output_dir.exists():
        logger.info(f"Removing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []

    logger.info(f"Generating {num_pdfs} prescription PDF files...")

    for i in range(1, num_pdfs + 1):
        # Generate prescription data
        prescription_data = generate_prescription_data(fake)

        # Create filename
        filename = f"prescription_{prescription_data['prescription_number']}_{i:04d}.pdf"
        output_path = output_dir / filename

        # Create PDF
        try:
            create_prescription_pdf(output_path, prescription_data)
            generated_files.append(output_path)
            logger.debug(f"Generated: {filename}")
        except Exception as e:
            logger.error(f"Failed to generate {filename}: {e}")

    logger.info(f"Successfully generated {len(generated_files)} PDF files in {output_dir}")
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

