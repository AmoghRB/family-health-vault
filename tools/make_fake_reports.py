"""OWNER: Pankaj Kumar B S

Generates synthetic lab report PDFs and prescriptions for testing.
Outputs to samples/ and writes samples/ground_truth.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUTPUT_DIR = Path(__file__).parent.parent / "samples"


def draw_header(c: canvas.Canvas, lab_title: str, patient: str, date: str, time: str | None = None) -> float:
    width, height = A4
    c.setFont("Helvetica-Bold", 15)
    c.drawString(20 * mm, height - 25 * mm, lab_title)

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, height - 32 * mm, f"Patient Name: {patient}")
    time_str = f" | Collection Time: {time}" if time else ""
    c.drawString(20 * mm, height - 38 * mm, f"Report Date: {date}{time_str}")

    c.setLineWidth(1)
    c.line(20 * mm, height - 42 * mm, width - 20 * mm, height - 42 * mm)
    return height - 50 * mm


# ------------------------------------------------------------------------------
# LAYOUT 1: Sunrise Diagnostics (Bordered Table)
# ------------------------------------------------------------------------------
def make_sunrise_pdf(path: Path, patient: str, date: str, time: str, tests: list[dict]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = draw_header(c, "SUNRISE DIAGNOSTICS & RESEARCH CENTRE", patient, date, time)

    # Table Header
    c.setFont("Helvetica-Bold", 10)
    c.drawString(25 * mm, y, "Investigation")
    c.drawString(90 * mm, y, "Observed Value")
    c.drawString(130 * mm, y, "Unit")
    c.drawString(160 * mm, y, "Reference Interval")
    y -= 4 * mm
    c.line(20 * mm, y, width - 20 * mm, y)
    y -= 6 * mm

    c.setFont("Helvetica", 9)
    for t in tests:
        c.drawString(25 * mm, y, str(t["raw_test"]))
        c.drawString(95 * mm, y, str(t["raw_value"]))
        c.drawString(130 * mm, y, str(t.get("raw_unit") or ""))
        c.drawString(160 * mm, y, str(t.get("ref_range") or ""))
        y -= 6 * mm
        c.setStrokeColor(colors.lightgrey)
        c.line(20 * mm, y + 2 * mm, width - 20 * mm, y + 2 * mm)
        c.setStrokeColor(colors.black)

    c.save()


# ------------------------------------------------------------------------------
# LAYOUT 2: ThyroPlus Labs (List Layout with SI Units)
# ------------------------------------------------------------------------------
def make_thyroplus_pdf(path: Path, patient: str, date: str, time: str, tests: list[dict]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    y = draw_header(c, "THYROPLUS LABORATORIES INDIA", patient, date, time)

    for t in tests:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(25 * mm, y, f"• {t['raw_test']}")
        c.setFont("Helvetica", 10)
        unit = t.get("raw_unit") or ""
        ref = f" (Ref: {t['ref_range']})" if t.get("ref_range") else ""
        c.drawString(100 * mm, y, f": {t['raw_value']} {unit}{ref}")
        y -= 7 * mm

    c.save()


# ------------------------------------------------------------------------------
# LAYOUT 3: Sri Sai Clinical Lab (Plain, Missing Units, DD-MM-YY Date)
# ------------------------------------------------------------------------------
def make_srisai_pdf(path: Path, patient: str, date_str: str, time: str, tests: list[dict]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    y = draw_header(c, "SRI SAI CLINICAL LABORATORY", patient, date_str, time)

    c.setFont("Courier-Bold", 10)
    c.drawString(20 * mm, y, "TEST DESCRIPTION            RESULT        UNITS")
    y -= 6 * mm

    c.setFont("Courier", 9)
    for t in tests:
        name = str(t["raw_test"]).ljust(26)
        val = str(t["raw_value"]).ljust(12)
        unit = str(t.get("raw_unit") or "").ljust(10)
        c.drawString(20 * mm, y, f"{name}{val}{unit}")
        y -= 6 * mm

    c.save()


# ------------------------------------------------------------------------------
# PRESCRIPTION GENERATOR
# ------------------------------------------------------------------------------
def make_prescription_pdf(path: Path, patient: str, doctor: str, date: str, meds: list[dict]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, height - 25 * mm, doctor)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, height - 30 * mm, "MBBS, MD (Internal Medicine) · Reg No: KMC-49210")
    c.drawString(20 * mm, height - 35 * mm, f"Patient: {patient} | Date: {date}")

    c.line(20 * mm, height - 38 * mm, width - 20 * mm, height - 38 * mm)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, height - 48 * mm, "Rx")

    y = height - 58 * mm
    c.setFont("Helvetica", 10)
    for i, med in enumerate(meds, 1):
        c.drawString(25 * mm, y, f"{i}. {med['name']} {med['dose']} — {med['instructions']}")
        y -= 8 * mm

    c.save()


# ------------------------------------------------------------------------------
# MAIN GENERATOR
# ------------------------------------------------------------------------------
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ground_truth: dict[str, dict] = {}

    # ==========================================================================
    # RAMESH KUMAR — 7 Lab Reports + 1 Prescription
    # Story: Fasting glucose & HbA1c rising; starts Metformin in Oct 2024;
    #        Creatinine climbs 0.9 -> 1.3 mg/dL. One 11:40 AM fasting anomaly.
    # ==========================================================================

    ramesh_reports = [
        (
            "ramesh_2024-03-11_sunrise.pdf",
            "sunrise",
            "2024-03-11",
            "08:15",
            [
                {"raw_test": "Glucose, Fasting (Plasma)", "raw_value": "105", "raw_unit": "mg/dL", "ref_range": "70-100", "test_id": "glucose_fasting", "canonical_val": 105.0},
                {"raw_test": "HbA1c", "raw_value": "6.1", "raw_unit": "%", "ref_range": "< 5.7", "test_id": "hba1c", "canonical_val": 6.1},
                {"raw_test": "Serum Creatinine", "raw_value": "0.9", "raw_unit": "mg/dL", "ref_range": "0.7-1.3", "test_id": "serum_creatinine", "canonical_val": 0.9},
                {"raw_test": "Blood Urea", "raw_value": "24", "raw_unit": "mg/dL", "ref_range": "15-40", "test_id": "blood_urea", "canonical_val": 24.0},
                {"raw_test": "Total Cholesterol", "raw_value": "210", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 210.0},
                {"raw_test": "HDL Cholesterol", "raw_value": "42", "raw_unit": "mg/dL", "ref_range": "> 40", "test_id": "hdl_cholesterol", "canonical_val": 42.0},
                {"raw_test": "LDL Cholesterol", "raw_value": "142", "raw_unit": "mg/dL", "ref_range": "< 100", "test_id": "ldl_cholesterol", "canonical_val": 142.0},
                {"raw_test": "Hemoglobin", "raw_value": "14.2", "raw_unit": "g/dL", "ref_range": "13-17", "test_id": "hemoglobin", "canonical_val": 14.2},
            ]
        ),
        (
            "ramesh_2024-07-15_thyroplus.pdf",
            "thyroplus",
            "2024-07-15",
            "08:30",
            [
                {"raw_test": "FBS", "raw_value": "6.1", "raw_unit": "mmol/L", "ref_range": "3.9-5.6", "test_id": "glucose_fasting", "canonical_val": 109.8},
                {"raw_test": "HbA1c", "raw_value": "6.3", "raw_unit": "%", "ref_range": "4.0-5.7", "test_id": "hba1c", "canonical_val": 6.3},
                {"raw_test": "Creatinine", "raw_value": "0.95", "raw_unit": "mg/dL", "ref_range": "0.7-1.3", "test_id": "serum_creatinine", "canonical_val": 0.95},
                {"raw_test": "Total Cholesterol", "raw_value": "215", "raw_unit": "mg/dL", "ref_range": "125-200", "test_id": "total_cholesterol", "canonical_val": 215.0},
                {"raw_test": "Triglycerides", "raw_value": "165", "raw_unit": "mg/dL", "ref_range": "< 150", "test_id": "triglycerides", "canonical_val": 165.0},
                {"raw_test": "SGPT", "raw_value": "32", "raw_unit": "U/L", "ref_range": "< 45", "test_id": "sgpt", "canonical_val": 32.0},
                {"raw_test": "SGOT", "raw_value": "28", "raw_unit": "U/L", "ref_range": "< 40", "test_id": "sgot", "canonical_val": 28.0},
                {"raw_test": "Total WBC Count", "raw_value": "6800", "raw_unit": "cells/cumm", "ref_range": "4000-11000", "test_id": "total_wbc", "canonical_val": 6800.0},
            ]
        ),
        (
            "ramesh_2025-01-20_srisai.pdf",
            "srisai",
            "20-01-25",
            "11:40",  # LATE FASTING ANOMALY
            [
                {"raw_test": "Blood Sugar F", "raw_value": "118", "raw_unit": None, "ref_range": "70-100", "test_id": "glucose_fasting", "canonical_val": 118.0},
                {"raw_test": "HbA1c", "raw_value": "6.6", "raw_unit": "%", "ref_range": "< 5.7", "test_id": "hba1c", "canonical_val": 6.6},
                {"raw_test": "Creatinine", "raw_value": "1.0", "raw_unit": "mg/dL", "ref_range": "0.7-1.3", "test_id": "serum_creatinine", "canonical_val": 1.0},
                {"raw_test": "Urea", "raw_value": "28", "raw_unit": "mg/dL", "ref_range": "15-40", "test_id": "blood_urea", "canonical_val": 28.0},
                {"raw_test": "Cholesterol Total", "raw_value": "195", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 195.0},
                {"raw_test": "LDL", "raw_value": "130", "raw_unit": "mg/dL", "ref_range": "< 100", "test_id": "ldl_cholesterol", "canonical_val": 130.0},
                {"raw_test": "Hb", "raw_value": "13.9", "raw_unit": "g/dL", "ref_range": "13-17", "test_id": "hemoglobin", "canonical_val": 13.9},
                {"raw_test": "ESR", "raw_value": "12", "raw_unit": "mm/hr", "ref_range": "0-20", "test_id": "esr", "canonical_val": 12.0},
            ]
        ),
        (
            "ramesh_2025-06-18_sunrise.pdf",
            "sunrise",
            "2025-06-18",
            "08:20",
            [
                {"raw_test": "Glucose, Fasting", "raw_value": "122", "raw_unit": "mg/dL", "ref_range": "70-100", "test_id": "glucose_fasting", "canonical_val": 122.0},
                {"raw_test": "Glycated Hemoglobin", "raw_value": "6.8", "raw_unit": "%", "ref_range": "< 5.7", "test_id": "hba1c", "canonical_val": 6.8},
                {"raw_test": "Serum Creatinine", "raw_value": "1.1", "raw_unit": "mg/dL", "ref_range": "0.7-1.3", "test_id": "serum_creatinine", "canonical_val": 1.1},
                {"raw_test": "Uric Acid", "raw_value": "5.4", "raw_unit": "mg/dL", "ref_range": "3.5-7.2", "test_id": "uric_acid", "canonical_val": 5.4},
                {"raw_test": "Total Cholesterol", "raw_value": "188", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 188.0},
                {"raw_test": "HDL Cholesterol", "raw_value": "44", "raw_unit": "mg/dL", "ref_range": "> 40", "test_id": "hdl_cholesterol", "canonical_val": 44.0},
                {"raw_test": "Triglycerides", "raw_value": "152", "raw_unit": "mg/dL", "ref_range": "< 150", "test_id": "triglycerides", "canonical_val": 152.0},
                {"raw_test": "Hemoglobin", "raw_value": "14.0", "raw_unit": "g/dL", "ref_range": "13-17", "test_id": "hemoglobin", "canonical_val": 14.0},
            ]
        ),
        (
            "ramesh_2025-11-25_thyroplus.pdf",
            "thyroplus",
            "2025-11-25",
            "08:45",
            [
                {"raw_test": "FBS", "raw_value": "6.9", "raw_unit": "mmol/L", "ref_range": "3.9-5.6", "test_id": "glucose_fasting", "canonical_val": 124.2},
                {"raw_test": "HbA1c", "raw_value": "6.9", "raw_unit": "%", "ref_range": "4.0-5.7", "test_id": "hba1c", "canonical_val": 6.9},
                {"raw_test": "Serum Creatinine", "raw_value": "1.18", "raw_unit": "mg/dL", "ref_range": "0.7-1.3", "test_id": "serum_creatinine", "canonical_val": 1.18},
                {"raw_test": "Blood Urea", "raw_value": "32", "raw_unit": "mg/dL", "ref_range": "15-40", "test_id": "blood_urea", "canonical_val": 32.0},
                {"raw_test": "LDL Cholesterol", "raw_value": "124", "raw_unit": "mg/dL", "ref_range": "< 100", "test_id": "ldl_cholesterol", "canonical_val": 124.0},
                {"raw_test": "SGPT", "raw_value": "35", "raw_unit": "U/L", "ref_range": "< 45", "test_id": "sgpt", "canonical_val": 35.0},
                {"raw_test": "Platelet Count", "raw_value": "240000", "raw_unit": "cells/cumm", "ref_range": "150000-450000", "test_id": "platelet_count", "canonical_val": 240000.0},
                {"raw_test": "Total Protein", "raw_value": "7.1", "raw_unit": "g/dL", "ref_range": "6.0-8.3", "test_id": "total_protein", "canonical_val": 7.1},
            ]
        ),
        (
            "ramesh_2026-04-12_srisai.pdf",
            "srisai",
            "12-04-26",
            "08:10",
            [
                {"raw_test": "Blood Sugar F", "raw_value": "129", "raw_unit": None, "ref_range": "70-100", "test_id": "glucose_fasting", "canonical_val": 129.0},
                {"raw_test": "HbA1c", "raw_value": "7.1", "raw_unit": "%", "ref_range": "< 5.7", "test_id": "hba1c", "canonical_val": 7.1},
                {"raw_test": "Creatinine", "raw_value": "1.24", "raw_unit": "mg/dL", "ref_range": "0.7-1.3", "test_id": "serum_creatinine", "canonical_val": 1.24},
                {"raw_test": "Urea", "raw_value": "36", "raw_unit": "mg/dL", "ref_range": "15-40", "test_id": "blood_urea", "canonical_val": 36.0},
                {"raw_test": "Total Cholesterol", "raw_value": "182", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 182.0},
                {"raw_test": "HDL", "raw_value": "45", "raw_unit": "mg/dL", "ref_range": "> 40", "test_id": "hdl_cholesterol", "canonical_val": 45.0},
                {"raw_test": "Hb", "raw_value": "13.6", "raw_unit": "g/dL", "ref_range": "13-17", "test_id": "hemoglobin", "canonical_val": 13.6},
                {"raw_test": "Calcium", "raw_value": "9.2", "raw_unit": "mg/dL", "ref_range": "8.5-10.5", "test_id": "serum_calcium", "canonical_val": 9.2},
            ]
        ),
        (
            "ramesh_2026-08-14_sunrise.pdf",
            "sunrise",
            "2026-08-14",
            "08:15",
            [
                {"raw_test": "Glucose, Fasting (Plasma)", "raw_value": "131", "raw_unit": "mg/dL", "ref_range": "70-100", "test_id": "glucose_fasting", "canonical_val": 131.0},
                {"raw_test": "HbA1c", "raw_value": "7.2", "raw_unit": "%", "ref_range": "< 5.7", "test_id": "hba1c", "canonical_val": 7.2},
                {"raw_test": "Serum Creatinine", "raw_value": "1.3", "raw_unit": "mg/dL", "ref_range": "0.7-1.3", "test_id": "serum_creatinine", "canonical_val": 1.3},
                {"raw_test": "Blood Urea", "raw_value": "39", "raw_unit": "mg/dL", "ref_range": "15-40", "test_id": "blood_urea", "canonical_val": 39.0},
                {"raw_test": "Total Cholesterol", "raw_value": "178", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 178.0},
                {"raw_test": "LDL Cholesterol", "raw_value": "121", "raw_unit": "mg/dL", "ref_range": "< 100", "test_id": "ldl_cholesterol", "canonical_val": 121.0},
                {"raw_test": "Serum Potassium", "raw_value": "4.6", "raw_unit": "mEq/L", "ref_range": "3.5-5.1", "test_id": "serum_potassium", "canonical_val": 4.6},
                {"raw_test": "Serum Sodium", "raw_value": "139", "raw_unit": "mEq/L", "ref_range": "136-145", "test_id": "serum_sodium", "canonical_val": 139.0},
            ]
        ),
    ]

    # ==========================================================================
    # LAKSHMI KUMAR — 7 Lab Reports + 1 Prescription
    # Story: Vitamin D severely deficient (14 ng/mL), starts supplements Oct 2024;
    #        steadily normalizes to 45+ ng/mL.
    # ==========================================================================

    lakshmi_reports = [
        (
            "lakshmi_2024-04-10_sunrise.pdf",
            "sunrise",
            "2024-04-10",
            "08:30",
            [
                {"raw_test": "TSH", "raw_value": "4.8", "raw_unit": "µIU/mL", "ref_range": "0.4-4.0", "test_id": "tsh", "canonical_val": 4.8},
                {"raw_test": "Total T3", "raw_value": "92", "raw_unit": "ng/dL", "ref_range": "80-200", "test_id": "total_t3", "canonical_val": 92.0},
                {"raw_test": "Total T4", "raw_value": "5.6", "raw_unit": "µg/dL", "ref_range": "4.5-12.0", "test_id": "total_t4", "canonical_val": 5.6},
                {"raw_test": "Hemoglobin", "raw_value": "11.6", "raw_unit": "g/dL", "ref_range": "12-16", "test_id": "hemoglobin", "canonical_val": 11.6},
                {"raw_test": "Calcium", "raw_value": "8.4", "raw_unit": "mg/dL", "ref_range": "8.5-10.5", "test_id": "serum_calcium", "canonical_val": 8.4},
                {"raw_test": "Total Cholesterol", "raw_value": "190", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 190.0},
                {"raw_test": "HDL Cholesterol", "raw_value": "48", "raw_unit": "mg/dL", "ref_range": "> 40", "test_id": "hdl_cholesterol", "canonical_val": 48.0},
                {"raw_test": "Total WBC Count", "raw_value": "6200", "raw_unit": "cells/cumm", "ref_range": "4000-11000", "test_id": "total_wbc", "canonical_val": 6200.0},
            ]
        ),
        (
            "lakshmi_2024-09-15_thyroplus.pdf",
            "thyroplus",
            "2024-09-15",
            "08:45",
            [
                {"raw_test": "TSH", "raw_value": "5.2", "raw_unit": "mIU/L", "ref_range": "0.4-4.0", "test_id": "tsh", "canonical_val": 5.2},
                {"raw_test": "Hemoglobin", "raw_value": "11.8", "raw_unit": "g/dL", "ref_range": "12-16", "test_id": "hemoglobin", "canonical_val": 11.8},
                {"raw_test": "Serum Calcium", "raw_value": "8.6", "raw_unit": "mg/dL", "ref_range": "8.5-10.5", "test_id": "serum_calcium", "canonical_val": 8.6},
                {"raw_test": "FBS", "raw_value": "5.1", "raw_unit": "mmol/L", "ref_range": "3.9-5.6", "test_id": "glucose_fasting", "canonical_val": 91.8},
                {"raw_test": "Creatinine", "raw_value": "0.78", "raw_unit": "mg/dL", "ref_range": "0.6-1.1", "test_id": "serum_creatinine", "canonical_val": 0.78},
                {"raw_test": "Total Cholesterol", "raw_value": "185", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 185.0},
                {"raw_test": "Triglycerides", "raw_value": "130", "raw_unit": "mg/dL", "ref_range": "< 150", "test_id": "triglycerides", "canonical_val": 130.0},
                {"raw_test": "ESR", "raw_value": "18", "raw_unit": "mm/hr", "ref_range": "0-20", "test_id": "esr", "canonical_val": 18.0},
            ]
        ),
        (
            "lakshmi_2025-02-14_srisai.pdf",
            "srisai",
            "14-02-25",
            "09:10",
            [
                {"raw_test": "TSH", "raw_value": "3.8", "raw_unit": "µIU/mL", "ref_range": "0.4-4.0", "test_id": "tsh", "canonical_val": 3.8},
                {"raw_test": "T4 Total", "raw_value": "7.2", "raw_unit": "µg/dL", "ref_range": "4.5-12.0", "test_id": "total_t4", "canonical_val": 7.2},
                {"raw_test": "Blood Sugar F", "raw_value": "94", "raw_unit": None, "ref_range": "70-100", "test_id": "glucose_fasting", "canonical_val": 94.0},
                {"raw_test": "Creatinine", "raw_value": "0.80", "raw_unit": "mg/dL", "ref_range": "0.6-1.1", "test_id": "serum_creatinine", "canonical_val": 0.8},
                {"raw_test": "Hb", "raw_value": "12.3", "raw_unit": "g/dL", "ref_range": "12-16", "test_id": "hemoglobin", "canonical_val": 12.3},
                {"raw_test": "Calcium", "raw_value": "9.1", "raw_unit": "mg/dL", "ref_range": "8.5-10.5", "test_id": "serum_calcium", "canonical_val": 9.1},
                {"raw_test": "SGPT", "raw_value": "22", "raw_unit": "U/L", "ref_range": "< 45", "test_id": "sgpt", "canonical_val": 22.0},
                {"raw_test": "Platelet Count", "raw_value": "280000", "raw_unit": "cells/cumm", "ref_range": "150000-450000", "test_id": "platelet_count", "canonical_val": 280000.0},
            ]
        ),
        (
            "lakshmi_2025-07-22_sunrise.pdf",
            "sunrise",
            "2025-07-22",
            "08:15",
            [
                {"raw_test": "TSH", "raw_value": "3.1", "raw_unit": "µIU/mL", "ref_range": "0.4-4.0", "test_id": "tsh", "canonical_val": 3.1},
                {"raw_test": "Total T3", "raw_value": "115", "raw_unit": "ng/dL", "ref_range": "80-200", "test_id": "total_t3", "canonical_val": 115.0},
                {"raw_test": "Total T4", "raw_value": "8.1", "raw_unit": "µg/dL", "ref_range": "4.5-12.0", "test_id": "total_t4", "canonical_val": 8.1},
                {"raw_test": "Hemoglobin", "raw_value": "12.8", "raw_unit": "g/dL", "ref_range": "12-16", "test_id": "hemoglobin", "canonical_val": 12.8},
                {"raw_test": "Serum Calcium", "raw_value": "9.4", "raw_unit": "mg/dL", "ref_range": "8.5-10.5", "test_id": "serum_calcium", "canonical_val": 9.4},
                {"raw_test": "Total Cholesterol", "raw_value": "175", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 175.0},
                {"raw_test": "HDL Cholesterol", "raw_value": "52", "raw_unit": "mg/dL", "ref_range": "> 40", "test_id": "hdl_cholesterol", "canonical_val": 52.0},
                {"raw_test": "Total Protein", "raw_value": "7.3", "raw_unit": "g/dL", "ref_range": "6.0-8.3", "test_id": "total_protein", "canonical_val": 7.3},
            ]
        ),
        (
            "lakshmi_2025-12-10_thyroplus.pdf",
            "thyroplus",
            "2025-12-10",
            "08:35",
            [
                {"raw_test": "TSH", "raw_value": "2.8", "raw_unit": "mIU/L", "ref_range": "0.4-4.0", "test_id": "tsh", "canonical_val": 2.8},
                {"raw_test": "FBS", "raw_value": "5.3", "raw_unit": "mmol/L", "ref_range": "3.9-5.6", "test_id": "glucose_fasting", "canonical_val": 95.4},
                {"raw_test": "Creatinine", "raw_value": "0.82", "raw_unit": "mg/dL", "ref_range": "0.6-1.1", "test_id": "serum_creatinine", "canonical_val": 0.82},
                {"raw_test": "Blood Urea", "raw_value": "22", "raw_unit": "mg/dL", "ref_range": "15-40", "test_id": "blood_urea", "canonical_val": 22.0},
                {"raw_test": "Total Cholesterol", "raw_value": "172", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 172.0},
                {"raw_test": "LDL Cholesterol", "raw_value": "98", "raw_unit": "mg/dL", "ref_range": "< 100", "test_id": "ldl_cholesterol", "canonical_val": 98.0},
                {"raw_test": "Serum Albumin", "raw_value": "4.2", "raw_unit": "g/dL", "ref_range": "3.5-5.0", "test_id": "serum_albumin", "canonical_val": 4.2},
                {"raw_test": "Hemoglobin", "raw_value": "13.0", "raw_unit": "g/dL", "ref_range": "12-16", "test_id": "hemoglobin", "canonical_val": 13.0},
            ]
        ),
        (
            "lakshmi_2026-05-15_srisai.pdf",
            "srisai",
            "15-05-26",
            "08:25",
            [
                {"raw_test": "TSH", "raw_value": "2.5", "raw_unit": "µIU/mL", "ref_range": "0.4-4.0", "test_id": "tsh", "canonical_val": 2.5},
                {"raw_test": "Blood Sugar F", "raw_value": "92", "raw_unit": None, "ref_range": "70-100", "test_id": "glucose_fasting", "canonical_val": 92.0},
                {"raw_test": "Creatinine", "raw_value": "0.81", "raw_unit": "mg/dL", "ref_range": "0.6-1.1", "test_id": "serum_creatinine", "canonical_val": 0.81},
                {"raw_test": "Calcium", "raw_value": "9.6", "raw_unit": "mg/dL", "ref_range": "8.5-10.5", "test_id": "serum_calcium", "canonical_val": 9.6},
                {"raw_test": "Hb", "raw_value": "13.2", "raw_unit": "g/dL", "ref_range": "12-16", "test_id": "hemoglobin", "canonical_val": 13.2},
                {"raw_test": "Total Cholesterol", "raw_value": "168", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 168.0},
                {"raw_test": "HDL", "raw_value": "54", "raw_unit": "mg/dL", "ref_range": "> 40", "test_id": "hdl_cholesterol", "canonical_val": 54.0},
                {"raw_test": "ESR", "raw_value": "10", "raw_unit": "mm/hr", "ref_range": "0-20", "test_id": "esr", "canonical_val": 10.0},
            ]
        ),
        (
            "lakshmi_2026-09-10_sunrise.pdf",
            "sunrise",
            "2026-09-10",
            "08:10",
            [
                {"raw_test": "TSH", "raw_value": "2.1", "raw_unit": "µIU/mL", "ref_range": "0.4-4.0", "test_id": "tsh", "canonical_val": 2.1},
                {"raw_test": "Total T3", "raw_value": "128", "raw_unit": "ng/dL", "ref_range": "80-200", "test_id": "total_t3", "canonical_val": 128.0},
                {"raw_test": "Total T4", "raw_value": "8.8", "raw_unit": "µg/dL", "ref_range": "4.5-12.0", "test_id": "total_t4", "canonical_val": 8.8},
                {"raw_test": "Glucose, Fasting", "raw_value": "90", "raw_unit": "mg/dL", "ref_range": "70-100", "test_id": "glucose_fasting", "canonical_val": 90.0},
                {"raw_test": "Serum Creatinine", "raw_value": "0.79", "raw_unit": "mg/dL", "ref_range": "0.6-1.1", "test_id": "serum_creatinine", "canonical_val": 0.79},
                {"raw_test": "Serum Calcium", "raw_value": "9.8", "raw_unit": "mg/dL", "ref_range": "8.5-10.5", "test_id": "serum_calcium", "canonical_val": 9.8},
                {"raw_test": "Hemoglobin", "raw_value": "13.4", "raw_unit": "g/dL", "ref_range": "12-16", "test_id": "hemoglobin", "canonical_val": 13.4},
                {"raw_test": "Total Cholesterol", "raw_value": "165", "raw_unit": "mg/dL", "ref_range": "< 200", "test_id": "total_cholesterol", "canonical_val": 165.0},
            ]
        ),
    ]

    # Generate all lab PDFs and store ground truth
    all_reports = [("Ramesh Kumar", ramesh_reports), ("Lakshmi Kumar", lakshmi_reports)]
    for patient_name, reports in all_reports:
        for filename, style, date, time, tests in reports:
            path = OUTPUT_DIR / filename
            if style == "sunrise":
                make_sunrise_pdf(path, patient_name, date, time, tests)
            elif style == "thyroplus":
                make_thyroplus_pdf(path, patient_name, date, time, tests)
            elif style == "srisai":
                make_srisai_pdf(path, patient_name, date, time, tests)

            ground_truth[filename] = {
                "patient": patient_name,
                "date": date,
                "time": time,
                "tests": [
                    {
                        "test_id": t["test_id"],
                        "raw_test": t["raw_test"],
                        "raw_value": t["raw_value"],
                        "raw_unit": t.get("raw_unit"),
                        "canonical_val": t["canonical_val"],
                    }
                    for t in tests
                ],
            }
            print(f"Generated lab report: {filename}")

    # ==========================================================================
    # PRESCRIPTIONS (2 Files)
    # ==========================================================================

    # 1. Ramesh: Metformin & Atorvastatin (Oct 2024)
    rx1_file = "ramesh_2024-10-01_rx.pdf"
    make_prescription_pdf(
        OUTPUT_DIR / rx1_file,
        "Ramesh Kumar",
        "Dr. Arvind K. Sharma, MD",
        "2024-10-01",
        [
            {"name": "Metformin", "dose": "500 mg", "instructions": "1 tab twice daily with meals (diabetes)"},
            {"name": "Atorvastatin", "dose": "10 mg", "instructions": "1 tab once daily at bedtime (cholesterol)"},
        ],
    )
    ground_truth[rx1_file] = {
        "patient": "Ramesh Kumar",
        "date": "2024-10-01",
        "kind": "prescription",
        "medicines": [
            {"name": "Metformin", "dose": "500 mg", "drug_class": "Biguanide"},
            {"name": "Atorvastatin", "dose": "10 mg", "drug_class": "Statin"},
        ],
    }
    print(f"Generated prescription: {rx1_file}")

    # 2. Lakshmi: Thyronorm & Uprise D3 (May 2024)
    rx2_file = "lakshmi_2024-05-01_rx.pdf"
    make_prescription_pdf(
        OUTPUT_DIR / rx2_file,
        "Lakshmi Kumar",
        "Dr. Meenakshi Sundaram, MD",
        "2024-05-01",
        [
            {"name": "Thyronorm", "dose": "25 mcg", "instructions": "1 tab daily morning empty stomach (hypothyroidism)"},
            {"name": "Uprise D3", "dose": "60,000 IU", "instructions": "1 capsule once weekly for 8 weeks (vitamin D deficiency)"},
        ],
    )
    ground_truth[rx2_file] = {
        "patient": "Lakshmi Kumar",
        "date": "2024-05-01",
        "kind": "prescription",
        "medicines": [
            {"name": "Thyronorm", "dose": "25 mcg", "drug_class": "Thyroid hormone"},
            {"name": "Uprise D3", "dose": "60,000 IU", "drug_class": "Vitamin supplement"},
        ],
    }
    print(f"Generated prescription: {rx2_file}")

    # Write ground_truth.json
    gt_path = OUTPUT_DIR / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
    print(f"\nSuccessfully wrote ground truth mapping to: {gt_path}")
    print(f"Total files generated: {len(ground_truth)} (14 lab reports + 2 prescriptions)")


if __name__ == "__main__":
    main()
