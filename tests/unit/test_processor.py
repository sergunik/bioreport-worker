from dataclasses import asdict
from unittest.mock import MagicMock

import pytest

from app.anonymization.models import AnonymizationResult, Artifact
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
    DeAnonymizeStep,
    ExtractArtifactsStep,
    ExtractTextStep,
    LoadDocumentStep,
    MarkFailedStep,
    MarkProcessingStep,
    NormalizeStep,
    PersistAnonymizedStep,
    PersistArtifactsStep,
    PersistFinalResultStep,
    PersistNormalizedStep,
    PersistParsedStep,
)


def _make_document() -> UploadedDocument:
    return UploadedDocument(
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
        artifacts=[
            Artifact(type="PERSON", original="John Doe", replacement="PERSON_1"),
        ],
        transliteration_mapping=[0, 1, 2],
    )
    norm_result = NormalizationResult(
        person=Person(name="PERSON_1"),
        diagnostic_date="2025-01-01",
        markers=[
            Marker(code="GLU", name="Glucose", value=NumericValue(number=5.1, unit="mmol/L"))
        ],
    )

    doc_repo.find_by_uuid.return_value = document
    file_loader.load.return_value = b"%PDF-fake"
    pdf_extractor.extract.return_value = "Patient John Doe"
    doc_repo.get_sensitive_words.return_value = ["john", "doe"]
    anonymizer.anonymize.return_value = anon_result
    artifacts_extractor.extract.return_value = {
        "artifacts": [{"type": "PERSON", "original": "John Doe", "replacement": "PERSON_1"}]
    }
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
        DeAnonymizeStep(),
        PersistFinalResultStep(doc_repo=doc_repo),
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

        processor.process(uploaded_document_uuid="abc-123", job_id=9)

        job_repo.mark_processing.assert_called_once_with(9)
        doc_repo.find_by_uuid.assert_called_once_with("abc-123")
        file_loader.load.assert_called_once()
        pdf_extractor.extract.assert_called_once_with(b"%PDF-fake")
        doc_repo.update_parsed_result.assert_called_once_with("abc-123", "Patient John Doe")
        doc_repo.get_sensitive_words.assert_called_once_with(10)
        anonymizer.anonymize.assert_called_once_with(
            "Patient John Doe",
            sensitive_words=["john", "doe"],
        )
        doc_repo.update_anonymized_text.assert_called_once_with(
            "abc-123",
            anonymized_result="Patient PERSON_1",
            transliteration_mapping=[0, 1, 2],
        )
        doc_repo.update_artifacts_payload.assert_called_once_with(
            "abc-123",
            artifacts_payload={
                "artifacts": [
                    {"type": "PERSON", "original": "John Doe", "replacement": "PERSON_1"}
                ]
            },
        )
        normalizer.normalize.assert_called_once_with("Patient PERSON_1")
        doc_repo.update_normalized_result.assert_called_once_with(
            "abc-123",
            normalized_result=asdict(normalizer.normalize.return_value),
        )
        doc_repo.update_final_result.assert_called_once()
        final_result = doc_repo.update_final_result.call_args.kwargs["final_result"]
        assert final_result["person"]["name"] == "John Doe"
        job_repo.mark_failed.assert_not_called()

    def test_final_result_is_de_anonymized(self) -> None:
        processor, _loader, doc_repo, _pdf, _anon, _normalizer, _job_repo = _make_pipeline()

        processor.process(uploaded_document_uuid="abc-123", job_id=9)

        final_call = doc_repo.update_final_result.call_args
        final_result = final_call.kwargs["final_result"]
        assert final_result["person"]["name"] == "John Doe"

    def test_marks_job_failed_and_reraises_on_step_error(self) -> None:
        processor, _loader, doc_repo, pdf_extractor, _anon, _norm, job_repo = _make_pipeline()
        pdf_extractor.extract.side_effect = PdfExtractionError("bad pdf")

        with pytest.raises(PdfExtractionError, match="bad pdf"):
            processor.process(uploaded_document_uuid="abc-123", job_id=7)

        job_repo.mark_processing.assert_called_once_with(7)
        job_repo.mark_failed.assert_called_once_with(7, "bad pdf")
        doc_repo.update_parsed_result.assert_not_called()
        doc_repo.update_anonymized_text.assert_not_called()
        doc_repo.update_artifacts_payload.assert_not_called()
        doc_repo.update_normalized_result.assert_not_called()
        doc_repo.update_final_result.assert_not_called()

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
        doc_repo.find_by_uuid.side_effect = lambda *_: (
            call_order.append("find_by_uuid"),
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
        doc_repo.update_anonymized_text.side_effect = (
            lambda *_args, **_kwargs: call_order.append("persist_anonymized")
        )
        doc_repo.update_artifacts_payload.side_effect = (
            lambda *_args, **_kwargs: call_order.append("persist_artifacts")
        )
        normalizer.normalize.side_effect = lambda *_: (
            call_order.append("normalize"),
            NormalizationResult(person=Person(name="PERSON_1")),
        )[1]
        doc_repo.update_normalized_result.side_effect = (
            lambda *_args, **_kwargs: call_order.append("persist_normalized")
        )
        doc_repo.update_final_result.side_effect = (
            lambda *_args, **_kwargs: call_order.append("persist_final")
        )

        processor.process(uploaded_document_uuid="abc-123", job_id=7)

        assert call_order[0] == "mark_processing"
