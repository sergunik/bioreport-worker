from unittest.mock import patch

import pytest

from app.pdf.factory import PdfExtractorFactory
from app.pdf.pdfplumber_adapter import PdfPlumberAdapter
from app.pdf.pymupdf_adapter import PyMuPdfAdapter


def _make_settings(pdf_engine: str):  # type: ignore[no-untyped-def]
    """Create a minimal Settings-like object with only pdf_engine."""
    with patch("app.config.settings.Settings") as mock_cls:
        settings = mock_cls.return_value
        settings.pdf_engine = pdf_engine
        return settings


class TestPdfExtractorFactory:
    def test_creates_pdfplumber_adapter(self) -> None:
        settings = _make_settings("pdfplumber")
        adapter = PdfExtractorFactory.create(settings)
        assert isinstance(adapter, PdfPlumberAdapter)

    def test_creates_pymupdf_adapter(self) -> None:
        settings = _make_settings("pymupdf")
        adapter = PdfExtractorFactory.create(settings)
        assert isinstance(adapter, PyMuPdfAdapter)

    def test_is_case_insensitive(self) -> None:
        settings = _make_settings("PdfPlumber")
        adapter = PdfExtractorFactory.create(settings)
        assert isinstance(adapter, PdfPlumberAdapter)

    def test_raises_for_unknown_engine(self) -> None:
        settings = _make_settings("unknown")
        with pytest.raises(ValueError, match="Unknown PDF engine"):
            PdfExtractorFactory.create(settings)
