import json

from app.anonymization.models import AnonymizationResult, Artifact
from app.processor.artifacts_extractor import ArtifactsExtractor


def test_extract_produces_correct_structure() -> None:
    extractor = ArtifactsExtractor()
    result = AnonymizationResult(
        anonymized_text="[PERSON_1] visited the clinic.",
        artifacts=[
            Artifact(type="PERSON", original="John Doe", replacement="[PERSON_1]"),
        ],
    )
    output = extractor.extract(result)
    assert output == {
        "artifacts": [
            {"type": "PERSON", "original": "John Doe", "replacement": "[PERSON_1]"}
        ]
    }


def test_extract_empty_artifacts() -> None:
    extractor = ArtifactsExtractor()
    result = AnonymizationResult(anonymized_text="No PII here.", artifacts=[])
    output = extractor.extract(result)
    assert output == {"artifacts": []}


def test_extract_multiple_artifact_types() -> None:
    extractor = ArtifactsExtractor()
    result = AnonymizationResult(
        anonymized_text="...",
        artifacts=[
            Artifact(type="PERSON", original="Alice", replacement="[PERSON_1]"),
            Artifact(
                type="EMAIL_ADDRESS",
                original="a@b.com",
                replacement="[EMAIL_ADDRESS_1]",
            ),
        ],
    )
    output = extractor.extract(result)
    assert len(output["artifacts"]) == 2
    types = {a["type"] for a in output["artifacts"]}
    assert types == {"PERSON", "EMAIL_ADDRESS"}


def test_extract_output_is_json_serializable() -> None:
    extractor = ArtifactsExtractor()
    result = AnonymizationResult(
        anonymized_text="x",
        artifacts=[
            Artifact(type="PERSON", original="Bob", replacement="[PERSON_1]"),
        ],
    )
    output = extractor.extract(result)
    serialized = json.dumps(output)
    assert '"artifacts"' in serialized
    parsed = json.loads(serialized)
    assert parsed["artifacts"][0]["type"] == "PERSON"
    assert parsed["artifacts"][0]["original"] == "Bob"
    assert parsed["artifacts"][0]["replacement"] == "[PERSON_1]"
