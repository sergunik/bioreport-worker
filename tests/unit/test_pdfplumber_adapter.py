import pytest

from app.pdf.exceptions import PdfExtractionError
from app.pdf.pdfplumber_adapter import PdfPlumberAdapter


class TestPdfPlumberAdapter:
    def test_extract_returns_text(self, sample_pdf_bytes: bytes) -> None:
        adapter = PdfPlumberAdapter()
        result = adapter.extract(sample_pdf_bytes)
        assert isinstance(result, str)
        assert "Hello PDF World" in result

    def test_extract_multi_page(self, multi_page_pdf_bytes: bytes) -> None:
        adapter = PdfPlumberAdapter()
        result = adapter.extract(multi_page_pdf_bytes)
        assert "Page one content" in result
        assert "Page two content" in result

    def test_extract_empty_pdf_returns_empty_string(self, empty_pdf_bytes: bytes) -> None:
        adapter = PdfPlumberAdapter()
        result = adapter.extract(empty_pdf_bytes)
        assert isinstance(result, str)
        assert result == ""

    def test_extract_raises_on_invalid_bytes(self) -> None:
        adapter = PdfPlumberAdapter()
        with pytest.raises(PdfExtractionError):
            adapter.extract(b"not a pdf")

    def test_extract_result_is_stripped(self, sample_pdf_bytes: bytes) -> None:
        adapter = PdfPlumberAdapter()
        result = adapter.extract(sample_pdf_bytes)
        assert result == result.strip()
