"""OWNER: Pankaj Kumar B S

Generates synthetic lab report PDFs for testing. Never commit real reports —
these are fabricated names and fabricated values only.
"""

from __future__ import annotations

import os
import random
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUTPUT_DIR = "sample_reports"

# Each "case" is (test name as this lab prints it, value, unit or None, printed range or None)
APOLLO_STYLE = [
    ("Glucose, Fasting (Plasma)", "108", "mg/dL", "70 - 100"),
    ("HbA1c", "6.1", "%", None),
    ("Creatinine", "1.1", "mg/dL", "0.6 - 1.3"),
    ("Total Cholesterol", "215", "mg/dL", "< 200"),
]

THYROCARE_STYLE = [
    ("FBS", "6.6", "mmol/L", None),          # needs unit conversion
    ("Glycated Hemoglobin", "7.2", "%", None),
    ("Serum Creatinine", "97.2", "umol/L", None),  # needs unit conversion
    ("TSH", "3.8", "mIU/L", "0.4 - 4.0"),
]

LOCAL_LAB_STYLE = [
    ("Blood Sugar F", "131", None, None),     # missing unit entirely — must guess
    ("Hb", "12.4", "g/dL", None),
    ("Creat", "1.4", None, None),              # missing unit — must guess
    ("Urea", "45", "mg/dL", "15 - 40"),
]

LAB_STYLES = {
    "sunrise_diagnostics": APOLLO_STYLE,
    "thyrocare_style": THYROCARE_STYLE,
    "local_lab": LOCAL_LAB_STYLE,
}

PATIENTS = ["Ramesh Kumar", "Lakshmi Iyer"]
DATES = ["2024-03-11", "2025-01-20", "2026-08-14"]


def make_pdf(path: str, patient: str, lab: str, date: str, collected_time: str, values: list[tuple]) -> None:
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 80

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, lab.replace("_", " ").title())
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Patient: {patient}")
    y -= 18
    c.drawString(50, y, f"Sample Date: {date}   Collected: {collected_time}")
    y -= 30

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Test")
    c.drawString(250, y, "Result")
    c.drawString(320, y, "Unit")
    c.drawString(400, y, "Reference Range")
    y -= 20

    c.setFont("Helvetica", 10)
    for test, value, unit, ref_range in values:
        c.drawString(50, y, test)
        c.drawString(250, y, value)
        c.drawString(320, y, unit or "")
        c.drawString(400, y, ref_range or "")
        y -= 18

    c.save()


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    random.seed(42)  # reproducible fake data

    for patient in PATIENTS:
        for i, date in enumerate(DATES):
            lab_name = list(LAB_STYLES.keys())[i % len(LAB_STYLES)]
            values = LAB_STYLES[lab_name]
            collected_time = "08:15" if i != 1 else "11:40"  # deliberately late "fasting" sample once

            filename = f"{patient.split()[0].lower()}_{date}_{lab_name}.pdf"
            path = os.path.join(OUTPUT_DIR, filename)
            make_pdf(path, patient, lab_name, date, collected_time, values)
            print(f"Generated: {path}")


if __name__ == "__main__":
    main()
