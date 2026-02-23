# BioReport Worker — Master Plan

## Context

Build a production-ready Python worker for parsing medical PDF documents. The system polls a PostgreSQL database for pending jobs, runs a linear pipeline (load → extract → anonymize → normalize → persist), and writes results back to the database. No Redis, no external queue — just `SELECT ... FOR UPDATE SKIP LOCKED`.

This plan is split into 7 sequential task files. Each task is independently deliverable and testable.

---

## Pending: Store Plan Files Into Project Repository

The 8 plan files currently live in `~/.claude/plans/` (Claude-local). They must be copied into the project repository so they are version-controlled, team-accessible, and co-located with the existing architecture doc.

### Target location

```
/Users/adamv/work/bioreport-worker/docs/plans/
```

This sits alongside the existing `docs/001-architecture-epic.md`.

### Files to copy (source → destination)

| Source (`~/.claude/plans/`) | Destination (`docs/plans/`) |
|-----------------------------|-----------------------------|
| `velvet-frolicking-garden.md` | `00-master-plan.md` |
| `task-01-core-architecture.md` | `task-01-core-architecture.md` |
| `task-02-load-file.md` | `task-02-load-file.md` |
| `task-03-pdf-extraction.md` | `task-03-pdf-extraction.md` |
| `task-04-anonymization.md` | `task-04-anonymization.md` |
| `task-05-artifacts.md` | `task-05-artifacts.md` |
| `task-06-normalization.md` | `task-06-normalization.md` |
| `task-07-persistence-deployment.md` | `task-07-persistence-deployment.md` |

### Implementation steps

1. Create directory `docs/plans/` inside the project
2. Write each file's content (already captured above) to the destination path
3. Verify: `ls docs/plans/` shows all 8 files

### Verification

```bash
ls /Users/adamv/work/bioreport-worker/docs/plans/
# Expected: 8 .md files
```

### Critical files

- Source: `/Users/adamv/.claude/plans/*.md` (8 files — content already known)
- Destination dir: `/Users/adamv/work/bioreport-worker/docs/plans/`
- Existing doc for reference: `/Users/adamv/work/bioreport-worker/docs/001-architecture-epic.md`

---

---

## Task Files

| # | File | Scope |
|---|------|-------|
| 1 | `task-01-core-architecture.md` | Project scaffold, config, DB, logging, worker loop, Docker, Makefile |
| 2 | `task-02-load-file.md` | Processor bootstrap + Step 1: fetch document, resolve path, read bytes |
| 3 | `task-03-pdf-extraction.md` | Step 2: PDF adapters (pdfplumber / pymupdf) + factory |
| 4 | `task-04-anonymization.md` | Step 3: Anonymizer adapter (Presidio) + AnonymizationResult model |
| 5 | `task-05-artifacts.md` | Step 4: Extract & persist PII artifacts to JSONB |
| 6 | `task-06-normalization.md` | Step 5: OpenAI normalizer adapter + rate-limit guard |
| 7 | `task-07-persistence-deployment.md` | Step 6–7: Final DB writes, retry policy, integration tests, prod Docker |

---

## Architecture Principles

- **SOLID** — every class has one reason to change
- **Adapter pattern** — PDF engine, anonymizer, normalizer are swappable via env
- **Dependency injection** — adapters passed to `Processor` constructor; no `import` coupling
- **Centralized config** — single `Settings` (Pydantic `BaseSettings`); loaded once at startup
- **No global state** — no module-level singletons except logger
- **Sync pipeline** — no asyncio; psycopg3 sync API throughout

---

## Project Structure

```
bioreport-worker/
├── app/
│   ├── config/
│   │   └── settings.py              # Pydantic BaseSettings
│   ├── database/
│   │   ├── connection.py            # psycopg3 connection pool
│   │   └── repositories/
│   │       ├── job_repository.py
│   │       └── uploaded_documents_repository.py
│   ├── logging/
│   │   └── logger.py                # Log.info / Log.error wrapper
│   ├── worker/
│   │   ├── worker.py                # Poll loop
│   │   └── job_runner.py            # Single-job orchestration + retry
│   ├── processor/
│   │   └── processor.py             # Linear pipeline: steps 1–7
│   ├── pdf/
│   │   ├── base.py
│   │   ├── pdfplumber_adapter.py
│   │   ├── pymupdf_adapter.py
│   │   └── factory.py
│   ├── anonymization/
│   │   ├── base.py
│   │   ├── models.py                # AnonymizationResult, Artifact
│   │   ├── presidio_adapter.py
│   │   └── factory.py
│   └── normalization/
│       ├── base.py
│       ├── models.py                # NormalizationResult, Marker
│       ├── openai_adapter.py
│       └── factory.py
├── tests/
│   ├── unit/
│   └── integration/
├── docker/
│   └── worker/
│       ├── Dockerfile.dev
│       └── Dockerfile.prod
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── .env.example
```

---

## Database Schema (reference)

### `pdf_jobs`
```
id, uploaded_document_id, status (pending|processing|done|failed),
attempts, error_message, locked_at, created_at, updated_at
```

### `uploaded_documents`
```
id, uuid, user_id, storage_disk (local|s3), file_size_bytes, mime_type,
file_hash_sha256, parsed_result, anonymised_result, anonymised_artifacts (JSONB),
normalized_result (JSONB), processed_at, created_at, updated_at
```

---

## Environment Variables

```
APP_ENV=dev
LOG_LEVEL=INFO
DB_HOST=host.docker.internal
DB_PORT=5432
DB_DATABASE=bioreport
DB_USERNAME=bioreport
DB_PASSWORD=secret
MAX_JOB_ATTEMPTS=3
JOB_POLL_INTERVAL_SECONDS=5
PDF_ENGINE=pdfplumber          # pdfplumber | pymupdf
OPENAI_API_KEY=
OPENAI_MODEL_NAME=
OPENAI_TIMEOUT_SECONDS=30
OPENAI_RATE_LIMIT_PER_MINUTE=60
```

---

## Core Pipeline (Processor)

```
processor.process(document_id, job_id)
  step 1 → load_file(document)       → bytes
  step 2 → extract_text(bytes)       → str
  step 3 → anonymize(text)           → AnonymizationResult
  step 4 → extract_artifacts(result) → list[Artifact]
  step 5 → normalize(anon_text)      → NormalizationResult
  step 6 → persist(document_id, ...)
  step 7 → mark_done(job_id)
```

Failure at any step raises an exception → caught by `job_runner` → retry logic applied.

---

## Quality Standards

| Standard | Requirement |
|----------|-------------|
| Type checking | `mypy --strict` passes |
| Linting | `ruff check` passes (no errors) |
| Unit coverage | ≥ 80% |
| Function size | ≤ 50 lines |
| Docstrings | All public classes and methods |
| Business logic | Never in worker loop — only in processor/adapters |

---

## Verification (End-to-End)

1. `make up` — starts worker container
2. `make lint` — ruff + mypy both pass
3. `make test` — all unit tests green
4. `make int-test` — integration tests with mocked adapters pass
5. Worker polls DB, picks up a `pending` job, runs pipeline, writes results, marks `done`
6. Retry: insert job with forced failure → verify `attempts` increments → verify `failed` after `MAX_JOB_ATTEMPTS`
