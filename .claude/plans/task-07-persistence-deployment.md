# Task 07 — Final Persistence, Retry Policy & Deployment

## Goal

Complete the pipeline: persist all results to `uploaded_documents` in a single `UPDATE`, mark the job as `done`, implement the retry/failure policy in `JobRunner`, write full integration tests, and finalize production Docker configuration.

---

## Deliverables

| File | Purpose |
|------|---------|
| `app/database/repositories/uploaded_documents_repository.py` | `save_results(...)` — single final UPDATE |
| `app/processor/processor.py` | Steps 6–7 wired in; full pipeline complete |
| `app/worker/job_runner.py` | Retry logic complete |
| `docker/worker/Dockerfile.prod` | Multi-stage, non-root, healthcheck, optimized |
| `docker-compose.yml` | Final with prod target and volumes |
| `tests/integration/test_full_pipeline.py` | Full pipeline integration test |
| `tests/integration/test_retry_behavior.py` | Retry + failure state machine test |
| `tests/integration/conftest.py` | DB fixtures, real Postgres connection |

---

## Step 6: Final Database Persist

### `app/database/repositories/uploaded_documents_repository.py` — `save_results`

Single `UPDATE` covering all pipeline outputs. Called only once, at the end of `process()`.

```python
def save_results(
    self,
    document_id: int,
    parsed_result: str,
    anonymised_result: str,
    anonymised_artifacts: dict[str, object],
    normalized_result: dict[str, object],
) -> None:
    """Persist all pipeline outputs in a single atomic UPDATE."""
    import json
    self._conn.execute(
        """
        UPDATE uploaded_documents
        SET
            parsed_result        = %s,
            anonymised_result    = %s,
            anonymised_artifacts = %s,
            normalized_result    = %s,
            processed_at         = NOW(),
            updated_at           = NOW()
        WHERE id = %s
        """,
        (
            parsed_result,
            anonymised_result,
            json.dumps(anonymised_artifacts),
            json.dumps(normalized_result),
            document_id,
        )
    )
    self._conn.commit()
```

---

## Step 7: Mark Job Done

### `app/database/repositories/job_repository.py` — `mark_done`

```python
def mark_done(self, job_id: int) -> None:
    """Mark job as done with current timestamp."""
    self._conn.execute(
        """
        UPDATE pdf_jobs
        SET status = 'done', updated_at = NOW()
        WHERE id = %s
        """,
        (job_id,)
    )
    self._conn.commit()
```

---

## Complete Processor Pipeline

### `app/processor/processor.py` — full implementation

```python
def process(self, document_id: int, job_id: int) -> None:
    """Execute the full document processing pipeline.

    Steps:
        1. Load file from disk
        2. Extract text from PDF
        3. Anonymize text
        4. Extract PII artifacts
        5. Normalize (extract medical markers)
        6. Persist all results
        7. Mark job done
    """
    with get_connection() as conn:
        doc_repo = UploadedDocumentsRepository(conn)
        job_repo = JobRepository(conn)

        # Step 1
        document = doc_repo.find_by_id(document_id)
        raw_bytes = self._file_loader.load(document)

        # Step 2
        extracted_text = self._pdf_extractor.extract(raw_bytes)

        # Step 3
        anonymization_result = self._anonymizer.anonymize(extracted_text)

        # Step 4
        artifacts = self._artifacts_extractor.extract(anonymization_result)

        # Step 5
        normalization_result = self._normalizer.normalize(
            anonymization_result.anonymized_text
        )

        # Step 6
        doc_repo.save_results(
            document_id=document_id,
            parsed_result=extracted_text,
            anonymised_result=anonymization_result.anonymized_text,
            anonymised_artifacts=artifacts,
            normalized_result=normalization_result.to_dict(),
        )

        # Step 7
        job_repo.mark_done(job_id)

    Log.info(f"Job {job_id} completed successfully", document_id=document_id)
```

**Design note:** All 7 steps share one DB connection opened at the start. The `save_results` and `mark_done` each commit explicitly. If an exception is raised at any step before Step 6, no partial writes occur.

---

## Retry Policy

### `app/worker/job_runner.py` — complete implementation

```python
class JobRunner:
    def __init__(
        self,
        processor: Processor,
        job_repo: JobRepository,
        settings: Settings,
    ) -> None:
        self._processor = processor
        self._job_repo = job_repo
        self._max_attempts = settings.max_job_attempts

    def run(self, job: JobRecord) -> None:
        """Execute one job; apply retry or failure policy on error."""
        Log.info(f"Starting job {job.id}", document_id=job.uploaded_document_id)
        try:
            self._processor.process(job.uploaded_document_id, job.id)
        except Exception as exc:
            Log.error(f"Job {job.id} failed: {exc}", exc_info=True)
            self._handle_failure(job, exc)

    def _handle_failure(self, job: JobRecord, exc: Exception) -> None:
        """Increment attempts. Retry if below max; mark failed otherwise."""
        new_attempts = job.attempts + 1
        with get_connection() as conn:
            repo = JobRepository(conn)
            if new_attempts >= self._max_attempts:
                repo.mark_failed(job.id, error_message=str(exc))
                Log.warning(
                    f"Job {job.id} permanently failed after {new_attempts} attempt(s)"
                )
            else:
                repo.increment_attempts_and_reset(job.id, new_attempts)
                Log.info(
                    f"Job {job.id} will retry (attempt {new_attempts}/{self._max_attempts})"
                )
```

### New repository method: `increment_attempts_and_reset`

```python
def increment_attempts_and_reset(self, job_id: int, new_attempts: int) -> None:
    """Return job to pending with incremented attempt counter."""
    self._conn.execute(
        """
        UPDATE pdf_jobs
        SET status = 'pending', attempts = %s, error_message = NULL, updated_at = NOW()
        WHERE id = %s
        """,
        (new_attempts, job_id)
    )
    self._conn.commit()
```

---

## Retry State Machine

```
pending → [claim] → processing → [success]  → done
                               → [fail, attempts < max] → pending (attempts++)
                               → [fail, attempts >= max] → failed
```

---

## Integration Tests

### `tests/integration/conftest.py`

```python
import pytest
import psycopg
from app.config.settings import Settings

@pytest.fixture(scope="session")
def settings():
    return Settings()

@pytest.fixture
def db_conn(settings):
    dsn = f"host={settings.db_host} dbname={settings.db_database} ..."
    with psycopg.connect(dsn) as conn:
        yield conn
        conn.rollback()  # clean up after each test

@pytest.fixture
def seed_document(db_conn):
    """Insert a test uploaded_document and return its ID."""
    ...

@pytest.fixture
def seed_job(db_conn, seed_document):
    """Insert a test pdf_job linked to seed_document."""
    ...
```

### `tests/integration/test_full_pipeline.py`

```python
def test_full_pipeline_marks_job_done(db_conn, seed_job, tmp_path):
    # Arrange: write a real PDF to tmp_path
    # Wire mocked adapters (PDF extractor, anonymizer, normalizer all mocked)
    # Act: run processor.process(document_id, job_id)
    # Assert: job status == 'done'
    # Assert: uploaded_documents.parsed_result is not null
    # Assert: uploaded_documents.normalized_result is not null
    # Assert: uploaded_documents.processed_at is not null

def test_full_pipeline_with_real_pdf_extractor(db_conn, seed_job, sample_pdf_path):
    # Uses real PdfPlumberAdapter, mocked anonymizer + normalizer
    ...
```

### `tests/integration/test_retry_behavior.py`

```python
def test_job_retries_on_failure(db_conn, seed_job, monkeypatch):
    # Force processor.process to raise an exception
    # Run job_runner.run(job) once
    # Assert: job.attempts == 1, job.status == 'pending'
    ...

def test_job_marked_failed_after_max_attempts(db_conn, seed_job, monkeypatch):
    # MAX_JOB_ATTEMPTS = 3
    # Run job_runner 3 times with forced failure
    # Assert: job.status == 'failed', job.attempts == 3
    ...

def test_retry_does_not_exceed_max_attempts(db_conn, seed_job, monkeypatch):
    # Verify no attempt is made after 'failed' status
    ...
```

---

## Production Docker

### `docker/worker/Dockerfile.prod`

```dockerfile
# Stage 1: Build
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install . \
 && python -m spacy download en_core_web_sm --target /install/lib/python3.12/site-packages

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

RUN useradd -m -u 1001 -s /bin/sh worker

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app/ ./app/

USER worker

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "from app.config.settings import Settings; Settings()" || exit 1

CMD ["python", "-m", "app.main"]
```

**Production image must NOT include:** ruff, mypy, pytest, test files, .env files, Makefile, docs/.

### `docker-compose.yml` prod target

```yaml
services:
  worker-prod:
    build:
      context: .
      dockerfile: docker/worker/Dockerfile.prod
    env_file: .env
    volumes:
      - ./files:/files:ro
    restart: unless-stopped
    networks:
      - bioreport
```

---

## Final Quality Checklist

### `make lint` — ruff + mypy

```
mypy app --strict
ruff check app tests
```

All must pass with zero errors or warnings.

### Coverage

```
pytest tests/unit --cov=app --cov-report=term-missing --cov-fail-under=80
```

### Makefile targets

All 6 targets must succeed cleanly:
- `make up` — containers start
- `make lint` — ruff + mypy pass
- `make lint-fix` — applies fixes
- `make test` — unit tests pass
- `make int-test` — integration tests pass

---

## Acceptance Criteria

- [ ] Full pipeline runs end-to-end with mocked adapters — job transitions `pending → done`
- [ ] `parsed_result`, `anonymised_result`, `anonymised_artifacts`, `normalized_result` all written
- [ ] `processed_at` is set on success
- [ ] Retry: failed job returns to `pending` with `attempts` incremented
- [ ] Final failure: `attempts >= MAX_JOB_ATTEMPTS` → status = `failed`, `error_message` set
- [ ] No retry attempted after `failed` status
- [ ] `make lint` passes (mypy strict + ruff)
- [ ] `make test` coverage ≥ 80%
- [ ] `make int-test` passes against real Postgres
- [ ] Production image size < 400MB (approximate target)
- [ ] Production image runs as non-root user (`worker`, uid 1001)
- [ ] Healthcheck passes on startup
