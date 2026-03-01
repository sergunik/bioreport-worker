from dataclasses import asdict

from app.anonymization.base import BaseAnonymizer
from app.database.repositories.job_repository import JobRepository
from app.database.repositories.uploaded_documents_repository import UploadedDocumentsRepository
from app.logging.logger import Log
from app.normalization.base import BaseNormalizer
from app.pdf.base import BasePdfExtractor
from app.processor.artifacts_extractor import ArtifactsExtractor
from app.processor.file_loader import FileLoader
from app.processor.pipeline import PipelineContext, PipelineStep


class MarkProcessingStep(PipelineStep):
    def __init__(self, job_repo: JobRepository) -> None:
        self._job_repo = job_repo

    def run(self, context: PipelineContext) -> PipelineContext:
        self._job_repo.mark_processing(context.job_id)
        Log.info(f"Job {context.job_id} marked as processing")
        return context


class MarkFailedStep(PipelineStep):
    def __init__(self, job_repo: JobRepository) -> None:
        self._job_repo = job_repo

    def run(self, context: PipelineContext) -> PipelineContext:
        self._job_repo.mark_failed(context.job_id, context.error_message)
        Log.error(f"Job {context.job_id} marked as failed: {context.error_message}")
        return context


class LoadDocumentStep(PipelineStep):
    def __init__(
        self,
        file_loader: FileLoader,
        doc_repo: UploadedDocumentsRepository,
    ) -> None:
        self._file_loader = file_loader
        self._doc_repo = doc_repo

    def run(self, context: PipelineContext) -> PipelineContext:
        document = self._doc_repo.find_by_id(context.uploaded_document_id)
        raw_bytes = self._file_loader.load(document)
        context.document = document
        context.raw_bytes = raw_bytes
        Log.info(
            f"Loaded {len(raw_bytes)} bytes for document {context.uploaded_document_id}"
        )
        return context


class ExtractTextStep(PipelineStep):
    def __init__(self, pdf_extractor: BasePdfExtractor) -> None:
        self._pdf_extractor = pdf_extractor

    def run(self, context: PipelineContext) -> PipelineContext:
        context.extracted_text = self._pdf_extractor.extract(context.raw_bytes)
        Log.info(
            f"Extracted {len(context.extracted_text)} chars from document "
            f"{context.uploaded_document_id}"
        )
        return context


class PersistParsedStep(PipelineStep):
    def __init__(self, doc_repo: UploadedDocumentsRepository) -> None:
        self._doc_repo = doc_repo

    def run(self, context: PipelineContext) -> PipelineContext:
        self._doc_repo.update_parsed_result(
            context.uploaded_document_id,
            context.extracted_text,
        )
        return context


class AnonymizeStep(PipelineStep):
    def __init__(
        self,
        anonymizer: BaseAnonymizer,
        doc_repo: UploadedDocumentsRepository,
    ) -> None:
        self._anonymizer = anonymizer
        self._doc_repo = doc_repo

    def run(self, context: PipelineContext) -> PipelineContext:
        if context.document is None:
            raise ValueError("PipelineContext.document must be set before anonymization")
        sensitive_words = self._doc_repo.get_sensitive_words(context.document.user_id)
        context.sensitive_words = sensitive_words
        Log.info(
            f"Loaded {len(sensitive_words)} sensitive words for user {context.document.user_id}"
        )
        context.anonymization_result = self._anonymizer.anonymize(
            context.extracted_text,
            sensitive_words=sensitive_words,
        )
        Log.info(
            f"Anonymized document {context.uploaded_document_id}: "
            f"{len(context.anonymization_result.artifacts)} artifacts found"
        )
        return context


class PersistAnonymizedStep(PipelineStep):
    def __init__(self, doc_repo: UploadedDocumentsRepository) -> None:
        self._doc_repo = doc_repo

    def run(self, context: PipelineContext) -> PipelineContext:
        if context.anonymization_result is None:
            raise ValueError("PipelineContext.anonymization_result must be set before persist")
        self._doc_repo.update_anonymized_text(
            context.uploaded_document_id,
            anonymized_result=context.anonymization_result.anonymized_text,
            transliteration_mapping=context.anonymization_result.transliteration_mapping,
        )
        return context


class ExtractArtifactsStep(PipelineStep):
    def __init__(self, artifacts_extractor: ArtifactsExtractor) -> None:
        self._artifacts_extractor = artifacts_extractor

    def run(self, context: PipelineContext) -> PipelineContext:
        if context.anonymization_result is None:
            raise ValueError(
                "PipelineContext.anonymization_result must be set before artifact extraction"
            )
        context.artifacts_payload = self._artifacts_extractor.extract(context.anonymization_result)
        return context


class PersistArtifactsStep(PipelineStep):
    def __init__(self, doc_repo: UploadedDocumentsRepository) -> None:
        self._doc_repo = doc_repo

    def run(self, context: PipelineContext) -> PipelineContext:
        self._doc_repo.update_artifacts_payload(
            context.uploaded_document_id,
            artifacts_payload=context.artifacts_payload,
        )
        return context


class NormalizeStep(PipelineStep):
    def __init__(self, normalizer: BaseNormalizer) -> None:
        self._normalizer = normalizer

    def run(self, context: PipelineContext) -> PipelineContext:
        if context.anonymization_result is None:
            raise ValueError(
                "PipelineContext.anonymization_result must be set before normalization"
            )
        result = self._normalizer.normalize(context.anonymization_result.anonymized_text)
        context.normalization_result = result
        Log.info(
            f"Normalized document {context.uploaded_document_id}: {len(result.markers)} markers"
        )
        return context


class PersistNormalizedStep(PipelineStep):
    def __init__(self, doc_repo: UploadedDocumentsRepository) -> None:
        self._doc_repo = doc_repo

    def run(self, context: PipelineContext) -> PipelineContext:
        if context.normalization_result is None:
            raise ValueError("PipelineContext.normalization_result must be set before persist")
        context.normalized_payload = asdict(context.normalization_result)
        self._doc_repo.update_normalized_result(
            context.uploaded_document_id,
            normalized_result=context.normalized_payload,
        )
        return context
