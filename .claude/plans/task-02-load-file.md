# Task 02 — Processor Step 1: Load File

## Goal

Implement the `Processor` class with only Step 1 active. Steps 2–7 are stubbed with `NotImplementedError` or pass-through mocks. The processor must:

1. Fetch the `uploaded_documents` record from the database
2. Resolve the file path on disk
3. Read and return the raw file bytes

All other pipeline steps remain unimplemented until subsequent tasks.

---

## Deliverables

| File | Purpose |
|------|---------|
| `app/processor/processor.py` | `Processor` class with `process()` + step 1 implemented |
| `app/database/repositories/uploaded_documents_repository.py` | `find_by_id(document_id)` returning `UploadedDocument` |
| `app/processor/models.py` | `UploadedDocument` dataclass, `ProcessorResult` dataclass |
| `app/processor/file_loader.py` | `FileLoader` — disk path resolution + file read |
| `tests/unit/test_processor.py` | Unit tests for processor step 1 |
| `tests/unit/test_file_loader.py` | Unit tests for FileLoader |
| `tests/unit/test_uploaded_documents_repository.py` | Repository unit tests |

---

## Database Schema Reference

### `uploaded_documents`
```
CREATE TABLE uploaded_documents (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    storage_disk VARCHAR(10) NOT NULL,   -- 'local' | 's3'
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(50) NOT NULL,       -- 'application/pdf'
    file_hash_sha256 CHAR(64) NOT NULL,
    parsed_result TEXT NULL,
    anonymised_result TEXT NULL,
    anonymised_artifacts JSONB NULL,
    normalized_result JSONB NULL,
    processed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### `pdf_jobs`
```
CREATE TABLE pdf_jobs (
    id BIGSERIAL PRIMARY KEY,
    uploaded_document_id BIGINT NOT NULL REFERENCES uploaded_documents(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NULL,
    locked_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT pdf_jobs_status_check CHECK (status IN ('pending','processing','done','failed'))
);
```

---

## Step-by-Step Implementation

### 1. `app/processor/models.py`

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class UploadedDocument:
    id: int
    uuid: str
    user_id: int
    storage_disk: str   # 'local' | 's3'
    file_hash_sha256: str
    mime_type: str
    file_size_bytes: int

@dataclass
class ProcessorResult:
    document_id: int
    raw_bytes: bytes
    extracted_text: str = ""
    anonymized_text: str = ""
    artifacts: list[dict[str, str]] = field(default_factory=list)
    normalized_result: dict[str, object] = field(default_factory=dict)
```

### 2. `app/database/repositories/uploaded_documents_repository.py`

```python
class UploadedDocumentsRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def find_by_id(self, document_id: int) -> UploadedDocument:
        """Fetch document record. Raises DocumentNotFoundError if missing."""
        row = self._conn.execute(
            "SELECT id, uuid, user_id, storage_disk, file_hash_sha256, mime_type, file_size_bytes "
            "FROM uploaded_documents WHERE id = %s",
            (document_id,)
        ).fetchone()

        if row is None:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        return UploadedDocument(
            id=row["id"],
            uuid=str(row["uuid"]),
            user_id=row["user_id"],
            storage_disk=row["storage_disk"],
            file_hash_sha256=row["file_hash_sha256"],
            mime_type=row["mime_type"],
            file_size_bytes=row["file_size_bytes"],
        )
```

Define `DocumentNotFoundError(Exception)` in `app/processor/exceptions.py`.

### 3. `app/processor/file_loader.py`

```python
class FileLoader:
    """Resolves filesystem path for a document and reads its bytes."""

    FILES_ROOT = Path("/files")

    def load(self, document: UploadedDocument) -> bytes:
        """Read document bytes from disk.

        Raises:
            FileNotFoundError: if the file does not exist at resolved path.
            UnsupportedStorageDiskError: if storage_disk is not 'local'.
        """
        if document.storage_disk != "local":
            raise UnsupportedStorageDiskError(
                f"storage_disk '{document.storage_disk}' is not supported"
            )
        path = self._resolve_path(document)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_bytes()

    def _resolve_path(self, document: UploadedDocument) -> Path:
        """Build path: /files/{uuid}.pdf"""
        return self.FILES_ROOT / f"{document.uuid}.pdf"
```

### 4. `app/processor/processor.py`

The `Processor` is the single orchestrator. Constructor receives all adapters. Steps that aren't implemented yet raise `NotImplementedError`.

```python
class Processor:
    """Orchestrates the full document processing pipeline."""

    def __init__(
        self,
        file_loader: FileLoader,
        pdf_extractor: BasePdfExtractor,           # Task 3
        anonymizer: BaseAnonymizer,                 # Task 4
        normalizer: BaseNormalizer,                 # Task 6
        doc_repo: UploadedDocumentsRepository,
        job_repo: JobRepository,
    ) -> None:
        self._file_loader = file_loader
        self._pdf_extractor = pdf_extractor
        self._anonymizer = anonymizer
        self._normalizer = normalizer
        self._doc_repo = doc_repo
        self._job_repo = job_repo

    def process(self, document_id: int, job_id: int) -> None:
        """Run the full pipeline for one document."""
        # Step 1: Load file
        document = self._doc_repo.find_by_id(document_id)
        raw_bytes = self._file_loader.load(document)

        # Steps 2–7: implemented in subsequent tasks
        raise NotImplementedError("Steps 2–7 not yet implemented")
```

At this stage, the processor is wired into `job_runner` but the test only exercises step 1 in isolation.

---

## File Path Convention

Files are stored at `/files/{uuid}.pdf`. The mount path `/files` is configurable via env:

```
FILES_ROOT=/files
```

Add `files_root: Path = Path("/files")` to `Settings`.

---

## Exceptions

All custom exceptions in `app/processor/exceptions.py`:

```python
class ProcessorError(Exception): ...
class DocumentNotFoundError(ProcessorError): ...
class UnsupportedStorageDiskError(ProcessorError): ...
class FileReadError(ProcessorError): ...
```

---

## Tests

### `tests/unit/test_file_loader.py`

```python
def test_load_returns_bytes_for_local_disk(tmp_path):
    loader = FileLoader(files_root=tmp_path)
    doc = UploadedDocument(..., storage_disk="local", uuid="abc-123")
    (tmp_path / "abc-123.pdf").write_bytes(b"%PDF test content")
    result = loader.load(doc)
    assert result == b"%PDF test content"

def test_load_raises_for_s3_disk():
    loader = FileLoader(files_root=Path("/files"))
    doc = UploadedDocument(..., storage_disk="s3")
    with pytest.raises(UnsupportedStorageDiskError):
        loader.load(doc)

def test_load_raises_when_file_missing(tmp_path):
    loader = FileLoader(files_root=tmp_path)
    doc = UploadedDocument(..., storage_disk="local", uuid="missing")
    with pytest.raises(FileNotFoundError):
        loader.load(doc)
```

### `tests/unit/test_uploaded_documents_repository.py`

- Mock `psycopg.Connection` with `MagicMock`
- `find_by_id` returns correct `UploadedDocument` when row exists
- `find_by_id` raises `DocumentNotFoundError` when row is `None`

### `tests/unit/test_processor.py`

- Mock all constructor dependencies
- `process()` calls `doc_repo.find_by_id(document_id)` with correct arg
- `process()` calls `file_loader.load(document)` with returned document
- `process()` raises `DocumentNotFoundError` if doc_repo raises it (propagates)

---

## Acceptance Criteria

- [ ] `make lint` passes
- [ ] `make test` — all new unit tests pass
- [ ] `FileLoader` reads real file in tmp dir (integration-style unit test)
- [ ] `Processor.process()` calls `find_by_id` and `load` in correct order
- [ ] `DocumentNotFoundError` propagates from repository through processor to job_runner
