"""Tests for de-anonymization of normalized payloads."""

from app.anonymization.de_anonymizer import de_anonymize_payload
from app.anonymization.models import Artifact


def _artifact(type_: str, original: str, replacement: str) -> Artifact:
    return Artifact(type=type_, original=original, replacement=replacement)


class TestDeAnonymizePayload:
    def test_replaces_person_name(self) -> None:
        artifacts = [_artifact("PERSON", "John Doe", "PERSON_1")]
        payload = {
            "person": {"name": "PERSON_1", "dob": "1990-01-01"},
            "markers": [],
        }
        result = de_anonymize_payload(payload, artifacts)
        assert result["person"]["name"] == "John Doe"

    def test_replaces_multiple_artifacts(self) -> None:
        artifacts = [
            _artifact("PERSON", "John Doe", "PERSON_1"),
            _artifact("EMAIL", "john@example.com", "EMAIL_1"),
        ]
        payload = {
            "person": {"name": "PERSON_1"},
            "contact": "EMAIL_1",
        }
        result = de_anonymize_payload(payload, artifacts)
        assert result["person"]["name"] == "John Doe"
        assert result["contact"] == "john@example.com"

    def test_replaces_in_nested_lists(self) -> None:
        artifacts = [_artifact("PERSON", "Jane Smith", "PERSON_1")]
        payload = {
            "pii": ["PERSON_1", "some date"],
        }
        result = de_anonymize_payload(payload, artifacts)
        assert result["pii"] == ["Jane Smith", "some date"]

    def test_no_artifacts_returns_unchanged(self) -> None:
        payload = {"person": {"name": "Test"}, "markers": []}
        result = de_anonymize_payload(payload, [])
        assert result == payload

    def test_preserves_non_string_values(self) -> None:
        artifacts = [_artifact("PERSON", "John", "PERSON_1")]
        payload = {
            "person": {"name": "PERSON_1"},
            "count": 42,
            "flag": True,
            "nothing": None,
        }
        result = de_anonymize_payload(payload, artifacts)
        assert result["count"] == 42
        assert result["flag"] is True
        assert result["nothing"] is None

    def test_replaces_partial_string_match(self) -> None:
        artifacts = [_artifact("PERSON", "John Doe", "PERSON_1")]
        payload = {"text": "Patient PERSON_1 visited on Monday"}
        result = de_anonymize_payload(payload, artifacts)
        assert result["text"] == "Patient John Doe visited on Monday"

    def test_replaces_in_deeply_nested_structures(self) -> None:
        artifacts = [_artifact("PERSON", "Jane", "PERSON_1")]
        payload = {
            "level1": {
                "level2": {
                    "level3": ["PERSON_1"],
                },
            },
        }
        result = de_anonymize_payload(payload, artifacts)
        assert result["level1"]["level2"]["level3"] == ["Jane"]

    def test_no_placeholders_in_payload_returns_unchanged(self) -> None:
        artifacts = [_artifact("PERSON", "John", "PERSON_1")]
        payload = {"text": "No placeholders here"}
        result = de_anonymize_payload(payload, artifacts)
        assert result["text"] == "No placeholders here"

    def test_longer_placeholder_replaced_before_shorter_avoids_collision(self) -> None:
        artifacts = [
            _artifact("PERSON", "Alice", "PERSON_1"),
            _artifact("PERSON", "Bob", "PERSON_10"),
        ]
        payload = {"names": ["PERSON_1", "PERSON_10"]}
        result = de_anonymize_payload(payload, artifacts)
        assert result["names"] == ["Alice", "Bob"]
