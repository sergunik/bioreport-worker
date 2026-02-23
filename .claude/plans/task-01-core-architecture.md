# Task 01 — Core Architecture & Infrastructure

## Goal

Establish the full project scaffold: dependencies, config, database layer, logging, job-polling worker loop, Docker images, and Makefile. No pipeline logic yet — only the skeleton that all subsequent tasks build on.

---

## Deliverables

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, all dependencies, ruff + mypy config |
| `.env.example` | All env vars with defaults |
| `app/config/settings.py` | Pydantic `BaseSettings` |
| `app/database/connection.py` | psycopg3 connection pool, context-managed transactions |
| `app/database/repositories/job_repository.py` | `claim_next_job`, `mark_processing`, `mark_done`, `mark_failed`, `increment_attempts` |
| `app/database/repositories/uploaded_documents_repository.py` | `find_by_id` |
| `app/logging/logger.py` | `Log` class with `info`, `warning`, `error`, `debug` |
| `app/worker/worker.py` | Poll loop: sleep → claim → dispatch |
| `app/worker/job_runner.py` | Run one job + catch exceptions + retry decision |
| `docker/worker/Dockerfile.dev` | Dev image with all tools |
| `docker/worker/Dockerfile.prod` | Multi-stage prod image |
| `docker-compose.yml` | Worker service wired to bioreport network |
| `Makefile` | up, down, exec, lint, lint-fix, test, int-test |
| `tests/unit/test_settings.py` | Config loading tests |
| `tests/unit/test_worker.py` | Poll loop unit tests |

---

## Step-by-Step Implementation

### 1. `pyproject.toml`

```toml
[project]
name = "bioreport-worker"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "psycopg[pool]>=3.2",
    "pydantic-settings>=2.7",
    "pdfplumber>=0.11",
    "pymupdf>=1.24",
    "presidio-analyzer>=2.2",
    "presidio-anonymizer>=2.2",
    "spacy>=3.8",
    "openai>=1.58",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "mypy>=1.13",
    "ruff>=0.8",
    "types-psycopg2",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "C90"]

[tool.mypy]
strict = true
python_version = "3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 2. `app/config/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"

    db_host: str
    db_port: int = 5432
    db_database: str
    db_username: str
    db_password: str

    max_job_attempts: int = 3
    job_poll_interval_seconds: int = 5

    pdf_engine: str = "pdfplumber"

    openai_api_key: str = ""
    openai_timeout_seconds: int = 30
    openai_rate_limit_per_minute: int = 60
```

Single global instance: `settings = Settings()` — module-level in `settings.py`, imported where needed.

### 3. `app/database/connection.py`

- Use `psycopg_pool.ConnectionPool`
- DSN built from `Settings`
- Expose `get_connection()` context manager returning a `psycopg.Connection`
- All DB calls use `with get_connection() as conn:` pattern
- Transactions: `conn.commit()` / `conn.rollback()` explicitly — never rely on auto-commit for job claiming

```python
from contextlib import contextmanager
import psycopg
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None

def init_pool(settings: Settings) -> None: ...

@contextmanager
def get_connection() -> Generator[psycopg.Connection, None, None]: ...
```

### 4. `app/database/repositories/job_repository.py`

Key method — job claiming (must commit immediately after lock):

```python
def claim_next_job(self, conn: psycopg.Connection) -> JobRecord | None:
    row = conn.execute("""
        SELECT id, uploaded_document_id, attempts
        FROM pdf_jobs
        WHERE status = 'pending'
          AND attempts < %s
        ORDER BY created_at
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """, (self._max_attempts,)).fetchone()

    if row is None:
        return None

    conn.execute("""
        UPDATE pdf_jobs
        SET status = 'processing', locked_at = NOW(), updated_at = NOW()
        WHERE id = %s
    """, (row["id"],))
    conn.commit()  # ← release lock immediately
    return JobRecord(...)
```

Other methods:
- `mark_done(job_id)` — status = done, updated_at = NOW()
- `mark_failed(job_id, error)` — status = failed, error_message, updated_at
- `increment_attempts(job_id)` — attempts += 1, status = pending, updated_at
- `find_by_id(job_id)` — for tests

### 5. `app/logging/logger.py`

```python
import logging
import sys
from app.config.settings import settings

class Log:
    _logger: logging.Logger = logging.getLogger("bioreport")

    @classmethod
    def info(cls, message: str, **kwargs: object) -> None: ...

    @classmethod
    def error(cls, message: str, **kwargs: object) -> None: ...

    @classmethod
    def warning(cls, message: str, **kwargs: object) -> None: ...

    @classmethod
    def debug(cls, message: str, **kwargs: object) -> None: ...
```

- Configurable log level from `settings.log_level`
- Structured format: `%(asctime)s [%(levelname)s] %(message)s`
- Handler: `StreamHandler(sys.stdout)` — Docker captures stdout
- Optional file handler configurable via env

### 6. `app/worker/worker.py`

```python
class Worker:
    def __init__(self, job_runner: JobRunner, settings: Settings) -> None: ...

    def run(self) -> None:
        """Main poll loop. Runs forever until interrupted."""
        while True:
            job = self._try_claim_job()
            if job:
                self._job_runner.run(job)
            else:
                time.sleep(self._settings.job_poll_interval_seconds)
```

- No business logic here — only poll + dispatch
- Catches `KeyboardInterrupt` for graceful shutdown
- Logs each poll cycle at DEBUG level

### 7. `app/worker/job_runner.py`

```python
class JobRunner:
    def __init__(self, processor: Processor, job_repo: JobRepository, settings: Settings) -> None: ...

    def run(self, job: JobRecord) -> None:
        try:
            self._processor.process(job.uploaded_document_id, job.id)
        except Exception as exc:
            self._handle_failure(job, exc)
```

- `_handle_failure`: increments attempts; if `attempts >= max` → `mark_failed`; else → back to `pending`

### 8. Docker

**`Dockerfile.dev`**:
```dockerfile
FROM python:3.12-slim
USER root
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e ".[dev]" && python -m spacy download en_core_web_sm
COPY . .
CMD ["python", "-m", "app.main"]
```

**`Dockerfile.prod`** (multi-stage):
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --prefix=/install .

FROM python:3.12-slim AS runtime
RUN useradd -m -u 1001 worker
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/
USER worker
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD ["python", "-c", "import app"]
CMD ["python", "-m", "app.main"]
```

### 9. `app/main.py`

Entry point: initialize pool → build dependencies → start worker loop.

```python
def main() -> None:
    settings = Settings()
    Log.configure(settings.log_level)
    init_pool(settings)
    processor = build_processor(settings)
    job_repo = JobRepository(settings.max_job_attempts)
    job_runner = JobRunner(processor, job_repo, settings)
    worker = Worker(job_runner, settings)
    worker.run()
```

---

## Tests

### Unit: `tests/unit/test_settings.py`
- All fields load from env correctly
- Defaults applied when env not set
- Invalid values raise `ValidationError`

### Unit: `tests/unit/test_worker.py`
- Worker calls `job_runner.run()` when job is claimed
- Worker sleeps when no job available
- Worker handles `KeyboardInterrupt` gracefully

### Unit: `tests/unit/test_job_runner.py`
- Calls `processor.process()` (mocked)
- On exception: calls `increment_attempts` when below max
- On exception: calls `mark_failed` when at max attempts

---

## Acceptance Criteria

- [ ] `make lint` — ruff + mypy both pass with zero errors
- [ ] `make test` — all unit tests green
- [ ] `make up` — container starts, worker logs "polling" without crashing
- [ ] Worker connects to Postgres (real DB in integration env)
- [ ] `make int-test` — integration tests pass
