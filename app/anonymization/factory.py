from app.anonymization.anonymizer import Anonymizer
from app.anonymization.base import BaseAnonymizer
from app.config.settings import Settings


class AnonymizerFactory:
    """Creates the configured anonymizer adapter."""

    @classmethod
    def create(cls, settings: Settings) -> BaseAnonymizer:
        """Create a deterministic ICU-based anonymizer."""
        _ = settings  # reserved for future configuration
        return Anonymizer()
