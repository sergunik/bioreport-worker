from dataclasses import asdict

from app.anonymization.base import BaseAnonymizer
from app.anonymization.factory import AnonymizerFactory
from app.config.settings import Settings
from app.database.repositories.uploaded_documents_repository import UploadedDocumentsRepository
from app.logging.logger import Log
from app.pdf.base import BasePdfExtractor
from app.pdf.factory import PdfExtractorFactory
from app.processor.file_loader import FileLoader


class Processor:
    """Orchestrates the full document processing pipeline.

    Pipeline: load -> extract -> anonymize -> normalize -> persist.
    Steps 4-7 are added in subsequent tasks.
    """

    def __init__(
        self,
        file_loader: FileLoader,
        doc_repo: UploadedDocumentsRepository,
        pdf_extractor: BasePdfExtractor,
        anonymizer: BaseAnonymizer,
    ) -> None:
        self._file_loader = file_loader
        self._doc_repo = doc_repo
        self._pdf_extractor = pdf_extractor
        self._anonymizer = anonymizer

    def process(self, uploaded_document_id: int, job_id: int) -> None:
        """Run the full processing pipeline for a document."""
        Log.info(f"Processing document {uploaded_document_id} for job {job_id}")

        # Step 1: Load file
        document = self._doc_repo.find_by_id(uploaded_document_id)
        raw_bytes = self._file_loader.load(document)
        Log.info(f"Loaded {len(raw_bytes)} bytes for document {uploaded_document_id}")

        # Step 2: Extract text and persist
        extracted_text = self._pdf_extractor.extract(raw_bytes)
        self._doc_repo.update_parsed_result(uploaded_document_id, extracted_text)
        Log.info(
            f"Extracted {len(extracted_text)} chars from document {uploaded_document_id}"
        )

        # Step 3: Fetch sensitive words for user
        sensitive_words = self._doc_repo.get_sensitive_words(document.user_id)
        Log.info(
            f"Loaded {len(sensitive_words)} sensitive words for user {document.user_id}"
        )

        # Step 4: Anonymize and persist
        anonymization_result = self._anonymizer.anonymize(
            extracted_text, sensitive_words=sensitive_words
        )
        self._doc_repo.update_anonymised_result(
            uploaded_document_id,
            anonymised_result=anonymization_result.anonymized_text,
            anonymised_artifacts=[asdict(a) for a in anonymization_result.artifacts],
            transliteration_mapping=anonymization_result.transliteration_mapping,
        )
        Log.info(
            f"Anonymized document {uploaded_document_id}: "
            f"{len(anonymization_result.artifacts)} artifacts found"
        )

        # Steps 5-7: implemented in subsequent tasks
        raise NotImplementedError("Steps 5-7 not yet implemented")


def build_processor(settings: Settings) -> Processor:
    """Build a Processor with all required adapters."""
    file_loader = FileLoader()
    doc_repo = UploadedDocumentsRepository()
    pdf_extractor = PdfExtractorFactory.create(settings)
    anonymizer = AnonymizerFactory.create(settings)
    return Processor(
        file_loader=file_loader,
        doc_repo=doc_repo,
        pdf_extractor=pdf_extractor,
        anonymizer=anonymizer,
    )
