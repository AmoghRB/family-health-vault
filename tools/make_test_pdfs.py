"""A few small fake reports for testing extraction, with an answer key.

OWNER: Extraction (Person 2): Amogh R B
LANGUAGE / LIBS: Python 3.12, ReportLab, json.
RUN: python tools/make_test_pdfs.py  → tests/fixtures/*.pdf + tests/fixtures/truth.json

Not the demo data (that's tools/make_fake_reports.py, Person 1). These exist so
extraction can be built and scored before the full fake set is ready. Three lab
layouts that are deliberately different, plus a prescription:
  sunrise  — bordered table: Test | Result | Unit | Reference Range (2 pages)
  thyroplus — dotted list "TEST NAME ........ value unit (range)"
  srisai   — plain "Name : value unit range", some units missing, dd-mm-yy dates
  prescription — doctor's Rx with doses printed (extraction must drop them)

truth.json holds values exactly AS PRINTED (strings), i.e. what extract.py should
return, so it can be scored without standard.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "fixtures"
W, H = A4

# (test, value, unit, range) exactly as each lab prints them
SUNRISE_P1 = [
    ("Fasting Blood Sugar", "112", "mg/dL", "70 - 100"),
    ("HbA1c", "6.1", "%", "< 5.7"),
    ("Total Cholesterol", "212", "mg/dL", "< 200"),
    ("HDL Cholesterol", "42", "mg/dL", "> 40"),
    ("LDL Cholesterol", "138", "mg/dL", "< 100"),
    ("Triglycerides", "165", "mg/dL", "< 150"),
]
SUNRISE_P2 = [
    ("Serum Creatinine", "0.9", "mg/dL", "0.6 - 1.3"),
    ("Blood Urea", "28", "mg/dL", "15 - 40"),
    ("TSH", "2.4", "µIU/mL", "0.4 - 4.0"),
    ("Haemoglobin", "13.8", "g/dL", "13 - 17"),
]
THYRO = [
    ("FBS", "6.9", "mmol/L", "3.9-5.6"),
    ("GLYCOSYLATED HAEMOGLOBIN", "6.8", "%", "4.0-5.6"),
    ("S. CREATININE", "97", "umol/L", "53-115"),
    ("TSH ULTRASENSITIVE", "3.1", "uIU/mL", "0.35-4.94"),
    ("VITAMIN D TOTAL", "18.5", "ng/mL", "30-100"),
    ("VITAMIN B12", "310", "pg/mL", "211-911"),
]
SRISAI = [
    ("Blood Sugar F", "131", None, "70-100"),
    ("HbA1c", "7.2", "%", None),
    ("S. Creatinine", "1.3", "mg/dL", "0.6 - 1.3"),
    ("Urea", "41", None, "15-40"),
    ("Hb", "13.1", "gm%", "13-17"),
    ("Platelet Count", "2,45,000", "/cumm", "1,50,000-4,50,000"),
]


def sunrise(path: Path) -> dict:
    c = canvas.Canvas(str(path), pagesize=A4)
    for page, rows in ((1, SUNRISE_P1), (2, SUNRISE_P2)):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, H - 50, "SUNRISE DIAGNOSTICS")
        c.setFont("Helvetica", 9)
        c.drawString(40, H - 64, "NABL accredited laboratory · 12 MG Road, Bengaluru")
        c.setFont("Helvetica", 10)
        c.drawString(40, H - 95, "Patient Name : Mr. Ramesh Kumar")
        c.drawString(330, H - 95, "Age / Sex : 58 Y / Male")
        c.drawString(40, H - 110, "Sample Collected : 11/03/2024 08:10 AM")
        c.drawString(330, H - 110, "Reported : 11/03/2024 02:45 PM")
        # table
        x = [40, 250, 330, 420, 555]
        y = H - 140
        c.setFont("Helvetica-Bold", 10)
        c.rect(x[0], y - 6, x[-1] - x[0], 20)
        for i, h in enumerate(["Test", "Result", "Unit", "Reference Range"]):
            c.drawString(x[i] + 5, y, h)
        c.setFont("Helvetica", 10)
        for test, value, unit, rng in rows:
            y -= 20
            c.rect(x[0], y - 6, x[-1] - x[0], 20)
            for i, cell in enumerate([test, value, unit, rng]):
                c.drawString(x[i] + 5, y, cell)
        for xx in x[1:-1]:
            c.line(xx, y - 6, xx, H - 126)
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(40, 40, f"Page {page} of 2 · This is a computer generated report.")
        c.showPage()
    c.save()
    return {"kind": "lab", "person": "Ramesh Kumar", "date": "2024-03-11",
            "collected_time": "08:10", "lab": "Sunrise Diagnostics",
            "values": [_v(r, 1) for r in SUNRISE_P1] + [_v(r, 2) for r in SUNRISE_P2]}


def thyroplus(path: Path) -> dict:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(40, H - 50, "ThyroPlus Labs Pvt. Ltd.")
    c.setFont("Helvetica", 10)
    c.drawString(40, H - 80, "NAME: RAMESH KUMAR (58Y/M)")
    c.drawString(40, H - 95, "SAMPLE COLLECTED ON: 20 Sep 2024  07:45")
    c.drawString(40, H - 110, "REF. BY: SELF")
    y = H - 150
    c.setFont("Courier", 10)
    for test, value, unit, rng in THYRO:
        c.drawString(40, y, f"{test} {'.' * (32 - len(test))} {value} {unit} ({rng})")
        y -= 18
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, 40, "*** End of report ***")
    c.save()
    return {"kind": "lab", "person": "Ramesh Kumar", "date": "2024-09-20",
            "collected_time": "07:45", "lab": "ThyroPlus Labs Pvt. Ltd.",
            "values": [_v(r, 1) for r in THYRO]}


def srisai(path: Path) -> dict:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, H - 50, "SRI SAI CLINICAL LABORATORY")
    c.setFont("Helvetica", 10)
    c.drawString(40, H - 80, "Pt. Name : Ramesh Kumar        Age/Sex : 58/M")
    c.drawString(40, H - 95, "Date : 14-08-26     Collection Time : 11:40 AM")
    y = H - 135
    for test, value, unit, rng in SRISAI:
        line = f"{test:<18} : {value}"
        if unit:
            line += f"  {unit}"
        if rng:
            line += f"   ({rng})"
        c.drawString(40, y, line)
        y -= 18
    c.drawString(40, y - 20, "Lab Technician")
    c.save()
    return {"kind": "lab", "person": "Ramesh Kumar", "date": "2026-08-14",
            "collected_time": "11:40", "lab": "Sri Sai Clinical Laboratory",
            "values": [_v(r, 1) for r in SRISAI]}


def prescription(path: Path) -> dict:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, H - 50, "Dr. Anil Rao, MBBS, MD (General Medicine)")
    c.setFont("Helvetica", 10)
    c.drawString(40, H - 66, "Rao Clinic · Jayanagar, Bengaluru")
    c.drawString(40, H - 100, "Patient: Ramesh Kumar      Age: 58      Date: 05/10/2024")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, H - 135, "Rx")
    c.setFont("Helvetica", 11)
    for i, line in enumerate(["Tab. Metformin 500mg        1-0-1   x 30 days",
                              "Tab. Atorvastatin 10 mg     0-0-1   x 30 days",
                              "Cap. Pantoprazole 40mg      1-0-0   before food"]):
        c.drawString(60, H - 160 - i * 20, line)
    c.drawString(40, H - 240, "Review after 1 month with FBS, HbA1c, S. Creatinine.")
    c.save()
    return {"kind": "prescription", "person": "Ramesh Kumar", "date": "2024-10-05",
            "collected_time": None, "lab": "Rao Clinic", "values": [],
            "medicines": [{"name": "Metformin"}, {"name": "Atorvastatin"},
                          {"name": "Pantoprazole"}]}


def _v(row: tuple, page: int) -> dict:
    test, value, unit, rng = row
    return {"test": test, "value": value, "unit": unit, "range": rng, "page": page}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    makers = {
        "ramesh_2024-03-11_sunrise.pdf": sunrise,
        "ramesh_2024-09-20_thyroplus.pdf": thyroplus,
        "ramesh_2026-08-14_srisai.pdf": srisai,
        "ramesh_2024-10-05_prescription.pdf": prescription,
    }
    truth = {}
    for name, make in makers.items():
        t = make(OUT / name)
        t.setdefault("medicines", [])
        truth[name] = t
    (OUT / "truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False))
    n = sum(len(t["values"]) for t in truth.values())
    print(f"wrote {len(truth)} PDFs, {n} values → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
