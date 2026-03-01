from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.anonymization.models import AnonymizationResult
from app.normalization.models import NormalizationResult
from app.processor.models import UploadedDocument


@dataclass(slots=True)
class PipelineContext:
    uploaded_document_id: int
    job_id: int
    document: UploadedDocument | None = None
    raw_bytes: bytes = b""
    extracted_text: str = ""
    sensitive_words: list[str] = field(default_factory=list)
    anonymization_result: AnonymizationResult | None = None
    artifacts_payload: dict[str, list[dict[str, str]]] = field(
        default_factory=lambda: {"artifacts": []}
    )
    normalization_result: NormalizationResult | None = None
    normalized_payload: dict[str, object] = field(default_factory=dict)
    error_message: str = ""


class PipelineStep(ABC):
    @abstractmethod
    def run(self, context: PipelineContext) -> PipelineContext:
        raise NotImplementedError
