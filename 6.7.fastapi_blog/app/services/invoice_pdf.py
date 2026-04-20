import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _fastapi_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def generate_invoice_pdf(
    *,
    billing_id: int,
    customer_name: str,
    plan_name: str,
    price_inr: Decimal,
    start_date: datetime,
    end_date: datetime,
    transaction_id: str,
) -> str:
    """
    Create a simple invoice PDF under /invoices/ and return path relative to project root.
    """
    invoices_dir = _fastapi_root() / "invoices"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"invoice_{billing_id}_{uuid.uuid4().hex[:8]}.pdf"
    abs_path = invoices_dir / safe_name

    c = canvas.Canvas(str(abs_path), pagesize=A4)
    width, height = A4
    y = height - 72
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, "INVOICE (Demo)")
    y -= 36
    c.setFont("Helvetica", 11)
    lines = [
        f"Transaction ID: {transaction_id}",
        f"Bill To: {customer_name}",
        f"Plan: {plan_name}",
        f"Amount: INR {price_inr}",
        f"Billing period: {start_date.isoformat()}  ->  {end_date.isoformat()}",
        "",
        "This is a computer-generated invoice for demonstration (ReportLab).",
    ]
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    c.showPage()
    c.save()
    return str(abs_path.resolve())
