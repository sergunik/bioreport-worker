from pathlib import Path

from app.anonymization.factory import AnonymizerFactory
from app.config.settings import Settings
from app.database.repositories.job_repository import JobRepository
from app.database.repositories.uploaded_documents_repository import UploadedDocumentsRepository
from app.logging.logger import Log
from app.normalization.factory import NormalizerFactory
from app.pdf.factory import PdfExtractorFactory
from app.processor.artifacts_extractor import ArtifactsExtractor
from app.processor.file_loader import FileLoader
from app.processor.pipeline import PipelineContext, PipelineStep
from app.processor.steps import (
    AnonymizeStep,
    ExtractArtifactsStep,
    ExtractTextStep,
    LoadDocumentStep,
    MarkFailedStep,
    MarkProcessingStep,
    NormalizeStep,
    PersistAnonymizedStep,
    PersistArtifactsStep,
    PersistNormalizedStep,
    PersistParsedStep,
)


class Processor:
    def __init__(
        self,
        steps: list[PipelineStep],
        failed_step: PipelineStep,
    ) -> None:
        self._steps = steps
        self._failed_step = failed_step

    def process(self, uploaded_document_id: int, job_id: int) -> None:
        Log.info(f"Processing document {uploaded_document_id} for job {job_id}")
        context = PipelineContext(
            uploaded_document_id=uploaded_document_id,
            job_id=job_id,
        )
        try:
            for step in self._steps:
                context = step.run(context)
        except Exception as exc:
            context.error_message = str(exc)
            self._failed_step.run(context)
            raise


def build_processor(
    settings: Settings,
    files_root: Path | None = None,
) -> Processor:
    """Build a Processor with all required adapters."""
    file_loader = FileLoader(files_root=files_root)
    doc_repo = UploadedDocumentsRepository()
    pdf_extractor = PdfExtractorFactory.create(settings)
    anonymizer = AnonymizerFactory.create(settings)
    normalizer = NormalizerFactory.create(settings)
    artifacts_extractor = ArtifactsExtractor()
    job_repo = JobRepository(max_attempts=settings.max_job_attempts)
    steps: list[PipelineStep] = [
        MarkProcessingStep(job_repo),
        LoadDocumentStep(file_loader=file_loader, doc_repo=doc_repo),
        ExtractTextStep(pdf_extractor=pdf_extractor),
        PersistParsedStep(doc_repo=doc_repo),
        AnonymizeStep(anonymizer=anonymizer, doc_repo=doc_repo),
        PersistAnonymizedStep(doc_repo=doc_repo),
        ExtractArtifactsStep(artifacts_extractor=artifacts_extractor),
        PersistArtifactsStep(doc_repo=doc_repo),
        NormalizeStep(normalizer=normalizer),
        PersistNormalizedStep(doc_repo=doc_repo),
    ]
    return Processor(steps=steps, failed_step=MarkFailedStep(job_repo))
