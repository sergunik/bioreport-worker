# Task 04 — Processor Step 3: Anonymization

## Goal

Implement the anonymization layer. Define the interface, result models, and a Presidio-based adapter. Wire Step 3 into the `Processor`. The anonymizer replaces PII tokens with labeled placeholders and returns structured artifact metadata.

---

## Deliverables

| File | Purpose |
|------|---------|
| `app/anonymization/base.py` | `BaseAnonymizer` abstract class |
| `app/anonymization/models.py` | `Artifact`, `AnonymizationResult` dataclasses |
| `app/anonymization/presidio_adapter.py` | Microsoft Presidio implementation |
| `app/anonymization/factory.py` | `AnonymizerFactory.create(settings)` |
| `app/anonymization/exceptions.py` | `AnonymizationError` |
| `app/processor/processor.py` | Step 3 wired in |
| `tests/unit/test_presidio_adapter.py` | Unit tests |
| `tests/unit/test_anonymization_models.py` | Model tests |
| `tests/unit/test_anonymizer_factory.py` | Factory tests |

---

## Data Models

### `app/anonymization/models.py`

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Artifact:
    """Single PII replacement record."""
    type: str           # e.g. "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"
    original: str       # original PII text
    replacement: str    # placeholder used in anonymized text, e.g. "[PERSON_1]"

@dataclass
class AnonymizationResult:
    """Output of the anonymizer step."""
    anonymized_text: str
    artifacts: list[Artifact] = field(default_factory=list)
```

**Artifact JSON format** (how it will be persisted in Task 5):
```json
{
  "type": "PERSON",
  "original": "John Doe",
  "replacement": "[PERSON_1]"
}
```

The replacement template is configurable. Default: `[{entity_type}_{counter}]`.

---

## Interface

### `app/anonymization/base.py`

```python
from abc import ABC, abstractmethod
from app.anonymization.models import AnonymizationResult

class BaseAnonymizer(ABC):
    """Contract for all anonymization adapters."""

    @abstractmethod
    def anonymize(self, text: str) -> AnonymizationResult:
        """Replace PII in text with labeled placeholders.

        Args:
            text: Plain text (output from PDF extractor).

        Returns:
            AnonymizationResult with anonymized text and artifact list.

        Raises:
            AnonymizationError: on any failure.
        """
```

---

## Presidio Adapter

### `app/anonymization/presidio_adapter.py`

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class PresidioAdapter(BaseAnonymizer):
    """Anonymizes text using Microsoft Presidio."""

    DEFAULT_ENTITIES = [
        "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
        "LOCATION", "DATE_TIME", "NRP", "IP_ADDRESS",
    ]

    def __init__(
        self,
        language: str = "en",
        entities: list[str] | None = None,
        replacement_template: str = "[{entity_type}_{counter}]",
    ) -> None:
        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()
        self._language = language
        self._entities = entities or self.DEFAULT_ENTITIES
        self._template = replacement_template
        self._counters: dict[str, int] = {}

    def anonymize(self, text: str) -> AnonymizationResult:
        try:
            return self._run(text)
        except Exception as exc:
            raise AnonymizationError(f"Presidio anonymization failed: {exc}") from exc

    def _run(self, text: str) -> AnonymizationResult:
        """Core logic — separate from error wrapping."""
        self._counters = {}
        results = self._analyzer.analyze(text, entities=self._entities, language=self._language)
        artifacts: list[Artifact] = []

        operators: dict[str, OperatorConfig] = {}
        for result in results:
            counter = self._counters.get(result.entity_type, 0) + 1
            self._counters[result.entity_type] = counter
            replacement = self._template.format(
                entity_type=result.entity_type, counter=counter
            )
            original = text[result.start:result.end]
            artifacts.append(Artifact(
                type=result.entity_type,
                original=original,
                replacement=replacement,
            ))
            operators[result.entity_type] = OperatorConfig(
                "replace", {"new_value": replacement}
            )

        anonymized = self._anonymizer.anonymize(
            text=text, analyzer_results=results, operators=operators
        )
        return AnonymizationResult(
            anonymized_text=anonymized.text,
            artifacts=artifacts,
        )
```

**Note:** The counter-per-entity-type approach means two different `PERSON` entities get `[PERSON_1]` and `[PERSON_2]`. Artifacts preserve the mapping.

### Replacement template configuration

Add to `Settings`:
```python
anonymization_replacement_template: str = "[{entity_type}_{counter}]"
```

Pass to `PresidioAdapter` constructor via factory.

---

## Factory

### `app/anonymization/factory.py`

```python
class AnonymizerFactory:
    @classmethod
    def create(cls, settings: Settings) -> BaseAnonymizer:
        """Currently only Presidio is supported."""
        return PresidioAdapter(
            replacement_template=settings.anonymization_replacement_template,
        )
```

If future adapters are added, route on a new `ANONYMIZER_ENGINE` env var.

---

## Wire Step 3 into Processor

```python
def process(self, document_id: int, job_id: int) -> None:
    # Step 1: Load file
    document = self._doc_repo.find_by_id(document_id)
    raw_bytes = self._file_loader.load(document)

    # Step 2: Extract text
    extracted_text = self._pdf_extractor.extract(raw_bytes)

    # Step 3: Anonymize
    anonymization_result = self._anonymizer.anonymize(extracted_text)

    # Steps 4–7: Not yet implemented
    raise NotImplementedError("Steps 4–7 not yet implemented")
```

---

## Tests

### `tests/unit/test_presidio_adapter.py`

```python
def test_anonymize_replaces_person_name():
    adapter = PresidioAdapter()
    result = adapter.anonymize("Patient John Doe visited the clinic.")
    assert "John Doe" not in result.anonymized_text
    assert any(a.type == "PERSON" and a.original == "John Doe" for a in result.artifacts)

def test_anonymize_returns_correct_replacement():
    adapter = PresidioAdapter(replacement_template="<{entity_type}>")
    result = adapter.anonymize("Email: user@example.com")
    assert "<EMAIL_ADDRESS>" in result.anonymized_text

def test_anonymize_empty_text_returns_empty():
    adapter = PresidioAdapter()
    result = adapter.anonymize("")
    assert result.anonymized_text == ""
    assert result.artifacts == []

def test_anonymize_raises_anonymization_error_on_failure(monkeypatch):
    adapter = PresidioAdapter()
    monkeypatch.setattr(adapter._analyzer, "analyze", side_effect=RuntimeError("fail"))
    with pytest.raises(AnonymizationError):
        adapter.anonymize("some text")
```

### `tests/unit/test_anonymization_models.py`

- `Artifact` is frozen (immutable)
- `AnonymizationResult` collects artifacts correctly
- JSON serialization produces correct structure (for Task 5 validation)

### `tests/unit/test_anonymizer_factory.py`

- Factory returns `PresidioAdapter` instance
- Replacement template from settings is passed through

---

## Acceptance Criteria

- [ ] `make lint` passes
- [ ] `make test` — all new unit tests pass
- [ ] `PresidioAdapter.anonymize()` replaces known PII types
- [ ] `Artifact` contains `type`, `original`, `replacement` for each PII token
- [ ] Empty or whitespace-only input returns empty result without error
- [ ] Any internal failure raises `AnonymizationError` (not raw exception)
- [ ] Replacement template is configurable via settings
