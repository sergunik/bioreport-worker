from abc import ABC, abstractmethod


class BasePdfExtractor(ABC):
    """Contract for all PDF text extraction adapters."""

    @abstractmethod
    def extract(self, pdf_bytes: bytes) -> str:
        """Extract plain text from PDF bytes.

        Args:
            pdf_bytes: Raw PDF file content.

        Returns:
            Extracted text as a single normalized string.

        Raises:
            PdfExtractionError: if extraction fails for any reason.
        """
