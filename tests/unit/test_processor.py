from dataclasses import asdict
from unittest.mock import MagicMock

import pytest

from app.anonymization.models import AnonymizationResult
from app.database.repositories.job_repository import JobRepository
from app.database.repositories.uploaded_documents_repository import UploadedDocumentsRepository
from app.normalization.models import Marker, NormalizationResult, NumericValue, Person
from app.pdf.exceptions import PdfExtractionError
from app.processor.artifacts_extractor import ArtifactsExtractor
from app.processor.file_loader import FileLoader
from app.processor.models import UploadedDocument
from app.processor.processor import Processor
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


def _make_document() -> UploadedDocument:
    return UploadedDocument(
        id=1,
        uuid="abc-123",
        user_id=10,
        storage_disk="local",
        file_hash_sha256="a" * 64,
        mime_type="application/pdf",
        file_size_bytes=1024,
    )


def _make_pipeline() -> tuple[
    Processor,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    file_loader = MagicMock(spec=FileLoader)
    doc_repo = MagicMock(spec=UploadedDocumentsRepository)
    pdf_extractor = MagicMock()
    anonymizer = MagicMock()
    artifacts_extractor = MagicMock(spec=ArtifactsExtractor)
    normalizer = MagicMock()
    job_repo = MagicMock(spec=JobRepository)

    document = _make_document()
    anon_result = AnonymizationResult(
        anonymized_text="Patient PERSON_1",
        artifacts=[],
        transliteration_mapping=[0, 1, 2],
    )
    norm_result = NormalizationResult(
        person=Person(name="PERSON_1"),
        diagnostic_date="2025-01-01",
        markers=[
            Marker(code="GLU", name="Glucose", value=NumericValue(number=5.1, unit="mmol/L"))
        ],
    )

    doc_repo.find_by_id.return_value = document
    file_loader.load.return_value = b"%PDF-fake"
    pdf_extractor.extract.return_value = "Patient John Doe"
    doc_repo.get_sensitive_words.return_value = ["john", "doe"]
    anonymizer.anonymize.return_value = anon_result
    artifacts_extractor.extract.return_value = {"artifacts": []}
    normalizer.normalize.return_value = norm_result

    steps = [
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
    processor = Processor(steps=steps, failed_step=MarkFailedStep(job_repo))
    return (
        processor,
        file_loader,
        doc_repo,
        pdf_extractor,
        anonymizer,
        normalizer,
        job_repo,
    )


class TestProcessorPipeline:
    def test_runs_all_steps_and_persists_outputs(self) -> None:
        processor, file_loader, doc_repo, pdf_extractor, anonymizer, normalizer, job_repo = (
            _make_pipeline()
        )

        processor.process(uploaded_document_id=1, job_id=9)

        job_repo.mark_processing.assert_called_once_with(9)
        doc_repo.find_by_id.assert_called_once_with(1)
        file_loader.load.assert_called_once()
        pdf_extractor.extract.assert_called_once_with(b"%PDF-fake")
        doc_repo.update_parsed_result.assert_called_once_with(1, "Patient John Doe")
        doc_repo.get_sensitive_words.assert_called_once_with(10)
        anonymizer.anonymize.assert_called_once_with(
            "Patient John Doe",
            sensitive_words=["john", "doe"],
        )
        doc_repo.update_anonymized_text.assert_called_once_with(
            1,
            anonymized_result="Patient PERSON_1",
            transliteration_mapping=[0, 1, 2],
        )
        doc_repo.update_artifacts_payload.assert_called_once_with(
            1,
            artifacts_payload={"artifacts": []},
        )
        normalizer.normalize.assert_called_once_with("Patient PERSON_1")
        doc_repo.update_normalized_result.assert_called_once_with(
            1,
            normalized_result=asdict(normalizer.normalize.return_value),
        )
        job_repo.mark_failed.assert_not_called()

    def test_marks_job_failed_and_reraises_on_step_error(self) -> None:
        processor, _loader, doc_repo, pdf_extractor, _anon, _norm, job_repo = _make_pipeline()
        pdf_extractor.extract.side_effect = PdfExtractionError("bad pdf")

        with pytest.raises(PdfExtractionError, match="bad pdf"):
            processor.process(uploaded_document_id=1, job_id=7)

        job_repo.mark_processing.assert_called_once_with(7)
        job_repo.mark_failed.assert_called_once_with(7, "bad pdf")
        doc_repo.update_parsed_result.assert_not_called()
        doc_repo.update_anonymized_text.assert_not_called()
        doc_repo.update_artifacts_payload.assert_not_called()
        doc_repo.update_normalized_result.assert_not_called()

    def test_mark_processing_runs_before_pipeline_work(self) -> None:
        (
            processor,
            file_loader,
            doc_repo,
            pdf_extractor,
            anonymizer,
            normalizer,
            job_repo,
        ) = _make_pipeline()
        call_order: list[str] = []

        job_repo.mark_processing.side_effect = lambda *_: call_order.append("mark_processing")
        doc_repo.find_by_id.side_effect = lambda *_: (
            call_order.append("find_by_id"),
            _make_document(),
        )[1]
        file_loader.load.side_effect = lambda *_: (call_order.append("load"), b"%PDF-fake")[1]
        pdf_extractor.extract.side_effect = lambda *_: (
            call_order.append("extract"),
            "Patient John Doe",
        )[1]
        doc_repo.update_parsed_result.side_effect = lambda *_: call_order.append("persist_parsed")
        doc_repo.get_sensitive_words.side_effect = lambda *_: (
            call_order.append("get_sensitive_words"),
            [],
        )[1]
        anonymizer.anonymize.side_effect = lambda *_args, **_kwargs: (
            call_order.append("anonymize"),
            AnonymizationResult(anonymized_text="anon", artifacts=[], transliteration_mapping=[]),
        )[1]
        doc_repo.update_anonymized_text.side_effect = lambda *_args, **_kwargs: call_order.append(
            "persist_anonymized"
        )
        doc_repo.update_artifacts_payload.side_effect = lambda *_args, **_kwargs: call_order.append(
            "persist_artifacts"
        )
        normalizer.normalize.side_effect = lambda *_: (
            call_order.append("normalize"),
            NormalizationResult(person=Person(name="PERSON_1")),
        )[1]
        doc_repo.update_normalized_result.side_effect = lambda *_args, **_kwargs: call_order.append(
            "persist_normalized"
        )

        processor.process(uploaded_document_id=1, job_id=7)

        assert call_order[0] == "mark_processing"
