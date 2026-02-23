from dataclasses import dataclass
from datetime import datetime


@dataclass
class JobRecord:
    """Represents a row from the pdf_jobs table."""

    id: int
    uploaded_document_id: int
    status: str
    attempts: int
    error_message: str | None = None
    locked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class DocumentRecord:
    """Represents a row from the uploaded_documents table."""

    id: int
    uuid: str
    user_id: int
    storage_disk: str
    file_size_bytes: int
    mime_type: str
    file_hash_sha256: str
    parsed_result: str | None = None
    anonymised_result: str | None = None
    anonymised_artifacts: str | None = None
    normalized_result: str | None = None
    processed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
