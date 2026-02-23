import pymupdf

from app.pdf.base import BasePdfExtractor
from app.pdf.exceptions import PdfExtractionError


class PyMuPdfAdapter(BasePdfExtractor):
    """Extracts text from PDF using PyMuPDF."""

    def extract(self, pdf_bytes: bytes) -> str:
        try:
            with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:  # type: ignore[no-untyped-call]
                pages = [page.get_text() for page in doc]
            return "\n".join(pages).strip()
        except PdfExtractionError:
            raise
        except Exception as exc:
            raise PdfExtractionError(f"pymupdf extraction failed: {exc}") from exc
