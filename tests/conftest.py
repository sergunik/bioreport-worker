import io

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


@pytest.fixture()
def sample_pdf_bytes() -> bytes:
    """Generate a minimal single-page PDF with known text content."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 720, "Hello PDF World")
    c.save()
    return buf.getvalue()


@pytest.fixture()
def multi_page_pdf_bytes() -> bytes:
    """Generate a two-page PDF with known text on each page."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 720, "Page one content")
    c.showPage()
    c.drawString(72, 720, "Page two content")
    c.save()
    return buf.getvalue()


@pytest.fixture()
def empty_pdf_bytes() -> bytes:
    """Generate a valid PDF with no text content (blank page)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.showPage()
    c.save()
    return buf.getvalue()
