import io

import pdfplumber

from app.pdf.base import BasePdfExtractor
from app.pdf.exceptions import PdfExtractionError


class PdfPlumberAdapter(BasePdfExtractor):
    """Extracts text from PDF using pdfplumber."""

    def extract(self, pdf_bytes: bytes) -> str:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages).strip()
        except PdfExtractionError:
            raise
        except Exception as exc:
            raise PdfExtractionError(f"pdfplumber extraction failed: {exc}") from exc
