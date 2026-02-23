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
