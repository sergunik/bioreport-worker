from unittest.mock import Mock

from app.anonymization.anonymizer import Anonymizer
from app.anonymization.factory import AnonymizerFactory
from app.config.settings import Settings


class TestAnonymizerFactory:
    def test_returns_anonymizer_instance(self) -> None:
        settings = Mock(spec=Settings)
        anonymizer = AnonymizerFactory.create(settings)
        assert isinstance(anonymizer, Anonymizer)
