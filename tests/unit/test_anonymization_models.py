import pytest

from app.anonymization.models import AnonymizationResult, Artifact


class TestArtifact:
    def test_stores_type_original_replacement(self) -> None:
        artifact = Artifact(type="PERSON", original="John Doe", replacement="[PERSON_1]")
        assert artifact.type == "PERSON"
        assert artifact.original == "John Doe"
        assert artifact.replacement == "[PERSON_1]"

    def test_is_frozen(self) -> None:
        artifact = Artifact(type="PERSON", original="John Doe", replacement="[PERSON_1]")
        with pytest.raises(AttributeError):
            artifact.type = "EMAIL_ADDRESS"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = Artifact(type="PERSON", original="John", replacement="[PERSON_1]")
        b = Artifact(type="PERSON", original="John", replacement="[PERSON_1]")
        assert a == b

    def test_inequality(self) -> None:
        a = Artifact(type="PERSON", original="John", replacement="[PERSON_1]")
        b = Artifact(type="PERSON", original="Jane", replacement="[PERSON_2]")
        assert a != b


class TestAnonymizationResult:
    def test_stores_anonymized_text(self) -> None:
        result = AnonymizationResult(anonymized_text="Hello [PERSON_1]")
        assert result.anonymized_text == "Hello [PERSON_1]"

    def test_default_artifacts_is_empty_list(self) -> None:
        result = AnonymizationResult(anonymized_text="text")
        assert result.artifacts == []

    def test_collects_artifacts(self) -> None:
        artifacts = [
            Artifact(type="PERSON", original="John", replacement="[PERSON_1]"),
            Artifact(type="EMAIL_ADDRESS", original="a@b.com", replacement="[EMAIL_ADDRESS_1]"),
        ]
        result = AnonymizationResult(anonymized_text="text", artifacts=artifacts)
        assert len(result.artifacts) == 2
        assert result.artifacts[0].type == "PERSON"
        assert result.artifacts[1].type == "EMAIL_ADDRESS"

    def test_artifacts_default_not_shared_between_instances(self) -> None:
        r1 = AnonymizationResult(anonymized_text="a")
        r2 = AnonymizationResult(anonymized_text="b")
        r1.artifacts.append(Artifact(type="PERSON", original="X", replacement="[PERSON_1]"))
        assert r2.artifacts == []

    def test_default_transliteration_mapping_is_empty_list(self) -> None:
        result = AnonymizationResult(anonymized_text="text")
        assert result.transliteration_mapping == []

    def test_stores_transliteration_mapping(self) -> None:
        result = AnonymizationResult(
            anonymized_text="text", transliteration_mapping=[0, 1, 2, 3]
        )
        assert result.transliteration_mapping == [0, 1, 2, 3]

    def test_transliteration_mapping_default_not_shared(self) -> None:
        r1 = AnonymizationResult(anonymized_text="a")
        r2 = AnonymizationResult(anonymized_text="b")
        r1.transliteration_mapping.append(42)
        assert r2.transliteration_mapping == []
