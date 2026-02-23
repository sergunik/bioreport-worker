# Task 06 — Processor Step 5: Normalization

## Goal

Implement the normalization layer. Extract structured medical markers from the anonymized text using OpenAI. The adapter uses sync HTTP, has a configurable timeout, and includes a simple rate-limit guard. Wire Step 5 into the `Processor`.

---

## Deliverables

| File | Purpose |
|------|---------|
| `app/normalization/base.py` | `BaseNormalizer` abstract class |
| `app/normalization/models.py` | `Marker`, `NormalizationResult` dataclasses |
| `app/normalization/openai_adapter.py` | OpenAI sync implementation |
| `app/normalization/rate_limiter.py` | Simple token-bucket rate limiter |
| `app/normalization/factory.py` | `NormalizerFactory.create(settings)` |
| `app/normalization/exceptions.py` | `NormalizationError` |
| `app/processor/processor.py` | Step 5 wired in |
| `tests/unit/test_openai_adapter.py` | Unit tests with mocked HTTP |
| `tests/unit/test_rate_limiter.py` | Rate limiter tests |
| `tests/unit/test_normalizer_factory.py` | Factory tests |

---

## Data Models

### `app/normalization/models.py`

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Marker:
    """Single extracted medical marker."""
    code: str    # e.g. "HBA1C", "WBC"
    name: str    # e.g. "Hemoglobin A1c", "White Blood Cell Count"
    value: str   # e.g. "6.2%", "4.5 × 10⁹/L"

@dataclass
class NormalizationResult:
    """Output of the normalizer step."""
    markers: list[Marker] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "markers": [
                {"code": m.code, "name": m.name, "value": m.value}
                for m in self.markers
            ]
        }
```

**Expected JSON format** (stored in `normalized_result` JSONB):
```json
{
  "markers": [
    {
      "code": "HBA1C",
      "name": "Hemoglobin A1c",
      "value": "6.2%"
    }
  ]
}
```

The expected result format is adjustable via a configurable prompt template.

---

## Interface

### `app/normalization/base.py`

```python
from abc import ABC, abstractmethod
from app.normalization.models import NormalizationResult

class BaseNormalizer(ABC):
    """Contract for all normalization adapters."""

    @abstractmethod
    def normalize(self, text: str) -> NormalizationResult:
        """Extract structured markers from anonymized medical text.

        Args:
            text: Anonymized plain text from the anonymizer step.

        Returns:
            NormalizationResult with a list of extracted Marker objects.

        Raises:
            NormalizationError: on any failure including HTTP errors.
        """
```

---

## Rate Limiter

### `app/normalization/rate_limiter.py`

Simple sliding-window counter + sleep approach. No threading, no asyncio.

```python
import time
from collections import deque

class RateLimiter:
    """Simple per-minute rate limiter using a sliding window."""

    def __init__(self, requests_per_minute: int) -> None:
        self._limit = requests_per_minute
        self._window = 60.0  # seconds
        self._timestamps: deque[float] = deque()

    def acquire(self) -> None:
        """Block until a request slot is available.

        Removes timestamps older than the window, then sleeps if at limit.
        """
        now = time.monotonic()
        # Evict old entries
        while self._timestamps and self._timestamps[0] < now - self._window:
            self._timestamps.popleft()

        if len(self._timestamps) >= self._limit:
            sleep_until = self._timestamps[0] + self._window
            sleep_for = sleep_until - now
            if sleep_for > 0:
                time.sleep(sleep_for)
            # Re-evict after sleep
            now = time.monotonic()
            while self._timestamps and self._timestamps[0] < now - self._window:
                self._timestamps.popleft()

        self._timestamps.append(time.monotonic())
```

---

## OpenAI Adapter

### `app/normalization/openai_adapter.py`

```python
import json
from openai import OpenAI
from app.normalization.base import BaseNormalizer
from app.normalization.models import Marker, NormalizationResult
from app.normalization.rate_limiter import RateLimiter
from app.normalization.exceptions import NormalizationError

DEFAULT_SYSTEM_PROMPT = """You are a medical data extraction assistant.
Extract all laboratory markers from the provided text.
Return a JSON object with a 'markers' array.
Each marker must have: code (short identifier), name (full name), value (with units).
Return ONLY the JSON object, no explanation."""

class OpenAiNormalizer(BaseNormalizer):
    """Normalizes medical text using OpenAI chat completion."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout: int = 30,
        rate_limiter: RateLimiter | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self._model = model
        self._rate_limiter = rate_limiter
        self._system_prompt = system_prompt

    def normalize(self, text: str) -> NormalizationResult:
        try:
            return self._call_api(text)
        except Exception as exc:
            raise NormalizationError(f"OpenAI normalization failed: {exc}") from exc

    def _call_api(self, text: str) -> NormalizationResult:
        if self._rate_limiter:
            self._rate_limiter.acquire()

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_response(content)

    def _parse_response(self, content: str) -> NormalizationResult:
        """Parse JSON response into NormalizationResult."""
        data = json.loads(content)
        markers = [
            Marker(
                code=item.get("code", ""),
                name=item.get("name", ""),
                value=item.get("value", ""),
            )
            for item in data.get("markers", [])
        ]
        return NormalizationResult(markers=markers)
```

### System prompt configurability

Add to `Settings`:
```python
normalization_system_prompt: str = ""  # empty = use DEFAULT_SYSTEM_PROMPT
openai_model: str = "gpt-4o-mini"
```

In factory, pass `system_prompt` from settings if non-empty.

---

## Factory

### `app/normalization/factory.py`

```python
class NormalizerFactory:
    @classmethod
    def create(cls, settings: Settings) -> BaseNormalizer:
        rate_limiter = RateLimiter(settings.openai_rate_limit_per_minute)
        return OpenAiNormalizer(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout=settings.openai_timeout_seconds,
            rate_limiter=rate_limiter,
            system_prompt=settings.normalization_system_prompt or DEFAULT_SYSTEM_PROMPT,
        )
```

---

## Wire Step 5 into Processor

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

    # Step 5: Normalize
    normalization_result = self._normalizer.normalize(anonymization_result.anonymized_text)

    # Steps 6–7: Not yet implemented
    raise NotImplementedError("Steps 6–7 not yet implemented")
```

---

## Tests

### `tests/unit/test_rate_limiter.py`

```python
def test_allows_requests_under_limit():
    limiter = RateLimiter(requests_per_minute=60)
    for _ in range(5):
        limiter.acquire()  # should not block

def test_tracks_timestamp_count():
    limiter = RateLimiter(requests_per_minute=10)
    for _ in range(10):
        limiter.acquire()
    assert len(limiter._timestamps) == 10
```

### `tests/unit/test_openai_adapter.py`

Use `unittest.mock.patch` to mock `openai.OpenAI`:

```python
def test_normalize_returns_markers(mock_openai_client):
    mock_openai_client.chat.completions.create.return_value = MockResponse(
        content='{"markers": [{"code": "HBA1C", "name": "Hemoglobin A1c", "value": "6.2%"}]}'
    )
    adapter = OpenAiNormalizer(api_key="test", rate_limiter=None)
    result = adapter.normalize("Patient HbA1c is 6.2%")
    assert len(result.markers) == 1
    assert result.markers[0].code == "HBA1C"

def test_normalize_raises_normalization_error_on_api_failure(mock_openai_client):
    mock_openai_client.chat.completions.create.side_effect = Exception("API down")
    adapter = OpenAiNormalizer(api_key="test")
    with pytest.raises(NormalizationError):
        adapter.normalize("some text")

def test_normalize_handles_empty_markers():
    # response with no markers
    adapter = OpenAiNormalizer(api_key="test")
    # mock returns {"markers": []}
    result = adapter.normalize("No markers here.")
    assert result.markers == []
```

### `tests/unit/test_normalizer_factory.py`

- Factory returns `OpenAiNormalizer` instance
- Rate limiter is injected with correct limit from settings

---

## Acceptance Criteria

- [ ] `make lint` passes
- [ ] `make test` — all new unit tests pass
- [ ] `OpenAiNormalizer` uses `response_format={"type": "json_object"}` (enforced JSON)
- [ ] Rate limiter prevents exceeding `openai_rate_limit_per_minute` calls per 60 seconds
- [ ] Any API or parsing failure raises `NormalizationError`
- [ ] `NormalizationResult.to_dict()` produces JSONB-compatible output
- [ ] System prompt is configurable via settings
- [ ] Step 5 wired after Step 4 in processor
