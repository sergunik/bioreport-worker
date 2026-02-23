from app.config.settings import Settings
from app.pdf.base import BasePdfExtractor
from app.pdf.pdfplumber_adapter import PdfPlumberAdapter
from app.pdf.pymupdf_adapter import PyMuPdfAdapter


class PdfExtractorFactory:
    """Creates the correct PDF extractor based on settings."""

    ADAPTERS: dict[str, type[BasePdfExtractor]] = {
        "pdfplumber": PdfPlumberAdapter,
        "pymupdf": PyMuPdfAdapter,
    }

    @classmethod
    def create(cls, settings: Settings) -> BasePdfExtractor:
        engine = settings.pdf_engine.lower()
        adapter_cls = cls.ADAPTERS.get(engine)
        if adapter_cls is None:
            raise ValueError(
                f"Unknown PDF engine '{engine}'. Choose from: {list(cls.ADAPTERS)}"
            )
        return adapter_cls()
