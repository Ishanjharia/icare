"""PDF generation for prescriptions and health records (fpdf2, Arogyamitra-style layout)."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from fpdf import FPDF


def _safe(s: str) -> str:
    """Latin-1 safe for core Helvetica (non-Latin replaced with '?')."""
    if not s:
        return ""
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _IcarePdf(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, _safe("I-CARE — rural India digital health"), align="C")


def generate_prescription_pdf(prescription: dict[str, Any]) -> bytes:
    """Build a single-page prescription PDF from a dict (DB row or API shape)."""
    pdf = _IcarePdf()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _safe("Prescription / प्रिस्क्रिप्शन"), ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)
    lines = [
        ("Patient ID", str(prescription.get("patient_id", ""))),
        ("Doctor", str(prescription.get("doctor_name") or prescription.get("doctor_id") or "—")),
        ("Medication", str(prescription.get("medication", ""))),
        ("Dosage", str(prescription.get("dosage", ""))),
        ("Instructions", str(prescription.get("instructions", ""))),
        ("Language", str(prescription.get("language", "en"))),
    ]
    if prescription.get("translated_text"):
        lines.append(("Translated", str(prescription.get("translated_text", ""))))
    for label, value in lines:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 8, _safe(f"{label}:"), ln=False)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 8, _safe(value))
        pdf.ln(1)
    pdf.set_font("Helvetica", "I", 9)
    pdf.ln(6)
    pdf.multi_cell(
        0,
        5,
        _safe(
            "This document is for information only. Follow your doctor's advice. "
            "This is not a medical diagnosis.",
        ),
    )
    ts = prescription.get("created_at")
    if isinstance(ts, datetime):
        pdf.ln(4)
        pdf.set_font("Helvetica", size=9)
        pdf.cell(0, 6, _safe(f"Generated: {ts.isoformat()}"), ln=True)
    elif isinstance(ts, str) and ts:
        pdf.ln(4)
        pdf.set_font("Helvetica", size=9)
        pdf.cell(0, 6, _safe(f"Generated: {ts[:40]}"), ln=True)
    out = pdf.output()
    if isinstance(out, bytes):
        return out
    if isinstance(out, bytearray):
        return bytes(out)
    return str(out).encode("latin-1")


def generate_health_record_pdf(record: dict[str, Any]) -> bytes:
    """Build a health record / report PDF from a dict."""
    pdf = _IcarePdf()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _safe("Health record / स्वास्थ्य रिकॉर्ड"), ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(40, 8, _safe("Type:"), ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 8, _safe(str(record.get("record_type", ""))))
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(40, 8, _safe("Description:"), ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 8, _safe(str(record.get("description", ""))))
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(40, 8, _safe("Language:"), ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, _safe(str(record.get("language", "en"))), ln=True)
    rd = record.get("report_data")
    if rd:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, _safe("Report data (JSON summary):"), ln=True)
        pdf.set_font("Courier", size=8)
        snippet = str(rd)[:4000]
        pdf.multi_cell(0, 4, _safe(snippet))
    vs = record.get("vitals_snapshot")
    if vs:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, _safe("Vitals snapshot:"), ln=True)
        pdf.set_font("Courier", size=8)
        pdf.multi_cell(0, 4, _safe(str(vs)[:2000]))
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0,
        5,
        _safe("I-CARE — for educational and continuity-of-care use. Consult a qualified clinician."),
    )
    pdf.ln(4)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 6, _safe(f"Exported: {datetime.now(timezone.utc).isoformat()}"), ln=True)
    out = pdf.output()
    if isinstance(out, bytes):
        return out
    if isinstance(out, bytearray):
        return bytes(out)
    return str(out).encode("latin-1")


def pdf_to_bytesio(data: bytes) -> BytesIO:
    bio = BytesIO(data)
    bio.seek(0)
    return bio
