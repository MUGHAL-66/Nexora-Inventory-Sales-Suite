"""PDF document helpers for invoice and table reports."""

from __future__ import annotations

from io import BytesIO
from typing import Any, Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_table_pdf(title: str, headers: Sequence[str], rows: Iterable[Sequence[object]]) -> bytes:
    """Build a small, styled PDF table and return its bytes for Streamlit download."""
    if not title.strip() or not headers:
        raise ValueError("A title and at least one table header are required.")
    data = [list(headers), *[list(row) for row in rows]]
    if any(len(row) != len(headers) for row in data):
        raise ValueError("Every table row must have the same number of values as the headers.")

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, title=title)
    styles = getSampleStyleSheet()
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3157C8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E6E8EF")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F5F0")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    document.build([Paragraph(title, styles["Title"]), Spacer(1, 16), table])
    return output.getvalue()


def build_sale_invoice_pdf(sale: dict[str, Any], items: Sequence[dict[str, Any]]) -> bytes:
    """Render a compact invoice PDF reflecting the finalized sale record."""
    if not sale:
        raise ValueError("Sale information is required to generate an invoice PDF.")
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, title=sale.get("invoice_number", "Invoice"))
    styles = getSampleStyleSheet()

    customer_name = sale.get("customer_name") or "Walk-in customer"
    invoice_number = sale.get("invoice_number", "INV")
    created_at = sale.get("created_at")
    invoice_date = created_at.strftime("%Y-%m-%d %H:%M") if created_at is not None else "N/A"

    rows = [
        ["SKU", "Product", "Qty", "Unit price", "Line total"],
    ]
    for item in items:
        rows.append(
            [
                str(item.get("sku", "")),
                str(item.get("product_name", "")),
                str(item.get("quantity", "0")),
                f"${float(item.get('unit_price', 0) or 0):.2f}",
                f"${float(item.get('line_total', 0) or 0):.2f}",
            ]
        )
    total_rows = [
        ["", "", "", "Subtotal", f"${float(sale.get('subtotal', 0) or 0):.2f}"],
        ["", "", "", "Discount", f"${float(sale.get('discount', 0) or 0):.2f}"],
        ["", "", "", "Total", f"${float(sale.get('total', 0) or 0):.2f}"],
    ]

    table = Table(rows, colWidths=[70, 190, 60, 90, 90], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3157C8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E6E8EF")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F5F0")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    summary = Table(total_rows, colWidths=[200, 60, 60, 90, 90], hAlign="RIGHT")
    summary.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#E6E8EF")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ]
        )
    )

    document.build(
        [
            Paragraph("Nexora Inventory & Sales Suite", styles["Title"]),
            Paragraph(f"Invoice {invoice_number}", styles["Heading2"]),
            Paragraph(f"Customer: {customer_name}", styles["BodyText"]),
            Paragraph(f"Created: {invoice_date}", styles["BodyText"]),
            Spacer(1, 10),
            table,
            Spacer(1, 12),
            summary,
        ]
    )
    return output.getvalue()
