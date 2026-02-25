from dataclasses import dataclass, field


@dataclass(frozen=True)
class UploadedDocument:
    """Domain model for an uploaded document (subset of DB columns)."""

    id: int
    uuid: str
    user_id: int
    storage_disk: str
    file_hash_sha256: str
    mime_type: str
    file_size_bytes: int


@dataclass
class ProcessorResult:
    """Accumulates data as the document moves through pipeline steps."""

    document_id: int
    raw_bytes: bytes = field(default_factory=bytes)
    extracted_text: str = ""
    anonymized_text: str = ""
    artifacts: dict[str, object] = field(default_factory=dict)
    normalized_result: dict[str, object] = field(default_factory=dict)
