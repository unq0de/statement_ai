#!/usr/bin/env python3
"""Generate synthetic bank-statement PDFs for local testing.

This creates valid minimal PDF files that contain realistic-looking banking data
without using any real personal or financial information.
"""

from __future__ import annotations

from pathlib import Path
import os


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "testdata"


def pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def make_pdf(path: Path, title: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    content_lines = [
        "BT",
        f"/F1 18 Tf 50 760 Td ({pdf_escape(title)}) Tj",
        "ET",
    ]

    y = 720
    for row in rows:
        content_lines.append("BT")
        content_lines.append(f"/F1 12 Tf 50 {y} Td ({pdf_escape(row)}) Tj")
        content_lines.append("ET")
        y -= 18

    content = "\n".join(content_lines)

    objects = []
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")
    objects.append(f"<< /Length {len(content.encode('latin-1'))} >>\nstream\n{content}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n{obj}\nendobj\n".encode("latin-1"))

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1"))

    path.write_bytes(pdf)


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)

    make_pdf(
        OUT_DIR / "statement_valid_1.pdf",
        "Synthetic Bank Statement 1",
        [
            "Account: 123456789",
            "Period: 2026-10-01 to 2026-10-31",
            "",
            "2026-10-02 | Groceries | -42.15 | CARD_PAYMENT",
            "2026-10-03 | Salary | 2400.00 | INCOME",
            "2026-10-07 | Rent | -980.00 | DIRECT_DEBIT",
            "2026-10-11 | Coffee Shop | -8.40 | CARD_PAYMENT",
            "2026-10-17 | Transfer | 200.00 | TRANSFER_IN",
        ],
    )

    make_pdf(
        OUT_DIR / "statement_valid_2.pdf",
        "Synthetic Bank Statement 2",
        [
            "Account: 987654321",
            "Period: 2026-11-01 to 2026-11-30",
            "",
            "2026-11-01 | Salary | 2500.00 | INCOME",
            "2026-11-03 | Supermarket | -64.75 | CARD_PAYMENT",
            "2026-11-05 | Gym | -29.90 | STANDING_ORDER",
            "2026-11-12 | Flight Booking | -210.00 | CARD_PAYMENT",
            "2026-11-19 | Freelance | 480.00 | INCOME",
            "2026-11-25 | Insurance | -55.00 | DIRECT_DEBIT",
        ],
    )

    make_pdf(
        OUT_DIR / "statement_invalid.pdf",
        "Not a real statement",
        [
            "This file is intentionally not a valid bank statement PDF.",
            "It is used to verify that invalid uploads are rejected.",
        ],
    )

    # Create a deliberately malformed PDF-like file to check validation paths.
    bad = OUT_DIR / "statement_malformed.pdf"
    bad.write_bytes(b"NOT A REAL PDF\nThis is only a text payload used for negative tests.")

    print(f"Synthetic test PDFs generated in: {OUT_DIR}")
    for p in sorted(OUT_DIR.glob("*.pdf")):
        print(f"- {p.name} ({p.stat().st_size} bytes)")
