from app.anonymization.anonymizer import Anonymizer
from app.anonymization.factory import AnonymizerFactory
from app.config.settings import Settings


class TestAnonymizerFactory:
    def test_returns_anonymizer_instance(self) -> None:
        settings = Settings()
        anonymizer = AnonymizerFactory.create(settings)
        assert isinstance(anonymizer, Anonymizer)
