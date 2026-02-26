from abc import ABC, abstractmethod

from app.normalization.models import NormalizationResult


class BaseNormalizer(ABC):
    """Contract for all normalization adapters."""

    @abstractmethod
    def normalize(self, text: str) -> NormalizationResult:
        """Transform anonymized medical text into structured data.

        Args:
            text: Anonymized plain text from the anonymization step.

        Returns:
            NormalizationResult with person, diagnostic_date, and markers.

        Raises:
            NormalizationError: on any failure.
        """
