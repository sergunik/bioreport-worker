# Task 05 — Processor Step 4: Artifacts Processing

## Goal

Extract structured PII metadata from the `AnonymizationResult` and persist it to the `anonymised_artifacts` JSONB column. This step transforms the list of `Artifact` objects into a serializable JSON structure and writes it to the database via the repository.

---

## Deliverables

| File | Purpose |
|------|---------|
| `app/processor/artifacts_extractor.py` | `ArtifactsExtractor` — transforms artifacts to JSON-serializable dicts |
| `app/database/repositories/uploaded_documents_repository.py` | `save_artifacts(document_id, artifacts)` method added |
| `app/processor/processor.py` | Step 4 wired in |
| `tests/unit/test_artifacts_extractor.py` | Unit tests for extractor |
| `tests/unit/test_uploaded_documents_repository.py` | Repository test for `save_artifacts` |

---

## Artifacts JSON Format

The final structure written to `anonymised_artifacts` (JSONB column):

```json
{
  "artifacts": [
    {
      "type": "PERSON",
      "original": "John Doe",
      "replacement": "[PERSON_1]"
    },
    {
      "type": "EMAIL_ADDRESS",
      "original": "john@example.com",
      "replacement": "[EMAIL_ADDRESS_1]"
    }
  ]
}
```

The top-level wrapper object allows future metadata fields (e.g., `total_count`, `detected_languages`) without breaking the schema.

---

## Step-by-Step Implementation

### 1. `app/processor/artifacts_extractor.py`

```python
from app.anonymization.models import Artifact, AnonymizationResult

class ArtifactsExtractor:
    """Converts anonymization artifacts to a JSON-serializable structure."""

    def extract(self, result: AnonymizationResult) -> dict[str, object]:
        """Transform AnonymizationResult artifacts into JSONB-ready dict.

        Returns:
            Dict with 'artifacts' key containing list of artifact dicts.
        """
        return {
            "artifacts": [self._artifact_to_dict(a) for a in result.artifacts]
        }

    def _artifact_to_dict(self, artifact: Artifact) -> dict[str, str]:
        return {
            "type": artifact.type,
            "original": artifact.original,
            "replacement": artifact.replacement,
        }
```

This class is intentionally simple — no DB access, no settings dependency. Pure data transformation.

### 2. `app/database/repositories/uploaded_documents_repository.py` — new method

```python
def save_artifacts(
    self,
    document_id: int,
    artifacts: dict[str, object],
    anonymised_result: str,
) -> None:
    """Persist anonymization results and artifacts to the database.

    Args:
        document_id: Target document ID.
        artifacts: JSONB-serializable artifacts dict.
        anonymised_result: Anonymized full text.
    """
    import json
    self._conn.execute(
        """
        UPDATE uploaded_documents
        SET
            anonymised_result = %s,
            anonymised_artifacts = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (anonymised_result, json.dumps(artifacts), document_id)
    )
```

**Note:** `anonymised_result` (the full anonymized text) and `anonymised_artifacts` are saved together in one `UPDATE` to minimize round-trips. This will be superseded in Task 7 by a single final `UPDATE` — but saving intermediately provides partial recovery info if desired.

**Decision point:** Intermediate saves vs single final save.

- **Recommended:** Do NOT save intermediately. Buffer all results in `ProcessorResult` and do a single `UPDATE` in Task 7. This keeps the pipeline transactionally clean.
- The repository method `save_artifacts` is implemented but called only from the final persist step.

### 3. Wire Step 4 into `app/processor/processor.py`

```python
def process(self, document_id: int, job_id: int) -> None:
    # Step 1: Load file
    document = self._doc_repo.find_by_id(document_id)
    raw_bytes = self._file_loader.load(document)

    # Step 2: Extract text
    extracted_text = self._pdf_extractor.extract(raw_bytes)

    # Step 3: Anonymize
    anonymization_result = self._anonymizer.anonymize(extracted_text)

    # Step 4: Extract artifacts
    artifacts = self._artifacts_extractor.extract(anonymization_result)

    # Steps 5–7: Not yet implemented
    raise NotImplementedError("Steps 5–7 not yet implemented")
```

Add `self._artifacts_extractor = ArtifactsExtractor()` to `Processor.__init__` — no injection needed since it has no external dependencies.

---

## ProcessorResult accumulation

Update `ProcessorResult` model (from Task 2) to hold all intermediate results:

```python
@dataclass
class ProcessorResult:
    document_id: int
    raw_bytes: bytes = field(default_factory=bytes)
    extracted_text: str = ""
    anonymized_text: str = ""
    artifacts: dict[str, object] = field(default_factory=dict)
    normalized_result: dict[str, object] = field(default_factory=dict)
```

The processor accumulates into this object and passes it to the final persist step in Task 7.

---

## Tests

### `tests/unit/test_artifacts_extractor.py`

```python
def test_extract_produces_correct_structure():
    extractor = ArtifactsExtractor()
    result = AnonymizationResult(
        anonymized_text="[PERSON_1] visited the clinic.",
        artifacts=[
            Artifact(type="PERSON", original="John Doe", replacement="[PERSON_1]"),
        ]
    )
    output = extractor.extract(result)
    assert output == {
        "artifacts": [
            {"type": "PERSON", "original": "John Doe", "replacement": "[PERSON_1]"}
        ]
    }

def test_extract_empty_artifacts():
    extractor = ArtifactsExtractor()
    result = AnonymizationResult(anonymized_text="No PII here.", artifacts=[])
    output = extractor.extract(result)
    assert output == {"artifacts": []}

def test_extract_multiple_artifact_types():
    extractor = ArtifactsExtractor()
    result = AnonymizationResult(
        anonymized_text="...",
        artifacts=[
            Artifact(type="PERSON", original="Alice", replacement="[PERSON_1]"),
            Artifact(type="EMAIL_ADDRESS", original="a@b.com", replacement="[EMAIL_ADDRESS_1]"),
        ]
    )
    output = extractor.extract(result)
    assert len(output["artifacts"]) == 2
    types = {a["type"] for a in output["artifacts"]}
    assert types == {"PERSON", "EMAIL_ADDRESS"}
```

### `tests/unit/test_uploaded_documents_repository.py` — additions

```python
def test_save_artifacts_executes_update(mock_conn):
    repo = UploadedDocumentsRepository(mock_conn)
    artifacts = {"artifacts": [{"type": "PERSON", "original": "X", "replacement": "[PERSON_1]"}]}
    repo.save_artifacts(document_id=1, artifacts=artifacts, anonymised_result="[PERSON_1] visited.")
    mock_conn.execute.assert_called_once()
    call_sql = mock_conn.execute.call_args[0][0]
    assert "anonymised_artifacts" in call_sql
    assert "anonymised_result" in call_sql
```

---

## Acceptance Criteria

- [ ] `make lint` passes
- [ ] `make test` — all artifact extractor tests pass
- [ ] `ArtifactsExtractor.extract()` returns correct JSONB-compatible dict
- [ ] Empty artifact list produces `{"artifacts": []}` — never `None`
- [ ] Output is directly serializable with `json.dumps()` (no custom types)
- [ ] `ProcessorResult` accumulates all intermediate state correctly
- [ ] Step 4 is wired into processor between Steps 3 and 5
