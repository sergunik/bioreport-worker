from abc import ABC, abstractmethod

from app.anonymization.models import AnonymizationResult


class BaseAnonymizer(ABC):
    """Contract for all anonymization adapters."""

    @abstractmethod
    def anonymize(
        self,
        text: str,
        sensitive_words: list[str] | None = None,
    ) -> AnonymizationResult:
        """Replace PII in text with labeled placeholders.

        Args:
            text: Plain text (output from PDF extractor).
            sensitive_words: Optional list of user-defined sensitive words
                             (lowercase tokens) for exact matching.

        Returns:
            AnonymizationResult with anonymized text and artifact list.

        Raises:
            AnonymizationError: on any failure.
        """
