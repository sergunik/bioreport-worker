from unittest.mock import MagicMock

import pytest

from app.anonymization.exceptions import AnonymizationError
from app.anonymization.models import AnonymizationResult, Artifact
from app.pdf.exceptions import PdfExtractionError
from app.processor.exceptions import DocumentNotFoundError
from app.processor.models import UploadedDocument
from app.processor.processor import Processor


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


def _make_processor() -> tuple[Processor, MagicMock, MagicMock, MagicMock, MagicMock]:
    mock_file_loader = MagicMock()
    mock_doc_repo = MagicMock()
    mock_doc_repo.get_sensitive_words.return_value = []
    mock_pdf_extractor = MagicMock()
    mock_anonymizer = MagicMock()
    mock_anonymizer.anonymize.return_value = AnonymizationResult(
        anonymized_text="", artifacts=[], transliteration_mapping=[]
    )
    processor = Processor(
        file_loader=mock_file_loader,
        doc_repo=mock_doc_repo,
        pdf_extractor=mock_pdf_extractor,
        anonymizer=mock_anonymizer,
    )
    return processor, mock_file_loader, mock_doc_repo, mock_pdf_extractor, mock_anonymizer


class TestProcessStep1:
    def test_calls_find_by_id_with_document_id(self) -> None:
        processor, _loader, mock_repo, _extractor, _anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=42, job_id=1)

        mock_repo.find_by_id.assert_called_once_with(42)

    def test_calls_file_loader_with_document(self) -> None:
        processor, mock_loader, mock_repo, _extractor, _anonymizer = _make_processor()
        document = _make_document()
        mock_repo.find_by_id.return_value = document

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_loader.load.assert_called_once_with(document)


class TestProcessStep2:
    def test_calls_pdf_extractor_with_raw_bytes(self) -> None:
        processor, mock_loader, mock_repo, mock_extractor, _anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_loader.load.return_value = b"%PDF-fake"
        mock_extractor.extract.return_value = "extracted text"

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_extractor.extract.assert_called_once_with(b"%PDF-fake")

    def test_persists_extracted_text(self) -> None:
        processor, mock_loader, mock_repo, mock_extractor, _anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_loader.load.return_value = b"%PDF-fake"
        mock_extractor.extract.return_value = "extracted text"

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=7, job_id=1)

        mock_repo.update_parsed_result.assert_called_once_with(7, "extracted text")

    def test_propagates_pdf_extraction_error(self) -> None:
        processor, _loader, mock_repo, mock_extractor, _anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.side_effect = PdfExtractionError("bad pdf")

        with pytest.raises(PdfExtractionError, match="bad pdf"):
            processor.process(uploaded_document_id=1, job_id=1)

    def test_does_not_persist_when_extraction_fails(self) -> None:
        processor, _loader, mock_repo, mock_extractor, _anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.side_effect = PdfExtractionError("bad pdf")

        with pytest.raises(PdfExtractionError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_repo.update_parsed_result.assert_not_called()


class TestProcessStep3SensitiveWords:
    def test_fetches_sensitive_words_for_user(self) -> None:
        processor, _loader, mock_repo, mock_extractor, _anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.return_value = "text"

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_repo.get_sensitive_words.assert_called_once_with(10)


class TestProcessStep4Anonymization:
    def test_calls_anonymizer_with_extracted_text_and_dictionary(self) -> None:
        processor, _loader, mock_repo, mock_extractor, mock_anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.return_value = "Patient John Doe"
        mock_repo.get_sensitive_words.return_value = ["john", "doe"]

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_anonymizer.anonymize.assert_called_once_with(
            "Patient John Doe", sensitive_words=["john", "doe"]
        )

    def test_persists_anonymised_result_and_artifacts(self) -> None:
        processor, _loader, mock_repo, mock_extractor, mock_anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.return_value = "Patient John Doe"
        mock_anonymizer.anonymize.return_value = AnonymizationResult(
            anonymized_text="Patient PERSON_1",
            artifacts=[
                Artifact(type="PERSON", original="John Doe", replacement="PERSON_1"),
            ],
            transliteration_mapping=[0, 1, 2],
        )

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=5, job_id=1)

        mock_repo.update_anonymised_result.assert_called_once_with(
            5,
            anonymised_result="Patient PERSON_1",
            anonymised_artifacts=[
                {"type": "PERSON", "original": "John Doe", "replacement": "PERSON_1"},
            ],
            transliteration_mapping=[0, 1, 2],
        )

    def test_persists_empty_artifacts_when_no_pii(self) -> None:
        processor, _loader, mock_repo, mock_extractor, mock_anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.return_value = "no pii here"
        mock_anonymizer.anonymize.return_value = AnonymizationResult(
            anonymized_text="no pii here", artifacts=[], transliteration_mapping=[]
        )

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_repo.update_anonymised_result.assert_called_once_with(
            1,
            anonymised_result="no pii here",
            anonymised_artifacts=[],
            transliteration_mapping=[],
        )

    def test_calls_steps_in_order(self) -> None:
        """Verify full pipeline call order."""
        processor, mock_loader, mock_repo, mock_extractor, mock_anonymizer = _make_processor()
        call_order: list[str] = []
        mock_repo.find_by_id.side_effect = lambda *a: (
            call_order.append("find_by_id"),
            _make_document(),
        )[1]
        mock_loader.load.side_effect = lambda *a: (
            call_order.append("load"),
            b"%PDF",
        )[1]
        mock_extractor.extract.side_effect = lambda *a: (
            call_order.append("extract"),
            "text",
        )[1]
        mock_repo.update_parsed_result.side_effect = lambda *a: (
            call_order.append("update_parsed_result"),
            None,
        )[1]
        mock_repo.get_sensitive_words.side_effect = lambda *_: (
            call_order.append("get_sensitive_words"),
            [],
        )[1]
        mock_anonymizer.anonymize.side_effect = lambda *_, **__: (
            call_order.append("anonymize"),
            AnonymizationResult(
                anonymized_text="anon", artifacts=[], transliteration_mapping=[]
            ),
        )[1]
        mock_repo.update_anonymised_result.side_effect = lambda *_, **__: (
            call_order.append("update_anonymised_result"),
            None,
        )[1]

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        assert call_order == [
            "find_by_id",
            "load",
            "extract",
            "update_parsed_result",
            "get_sensitive_words",
            "anonymize",
            "update_anonymised_result",
        ]

    def test_raises_not_implemented_after_anonymization(self) -> None:
        processor, _loader, mock_repo, mock_extractor, _anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.return_value = "text"

        with pytest.raises(NotImplementedError, match="Steps 5"):
            processor.process(uploaded_document_id=1, job_id=1)

    def test_propagates_anonymization_error(self) -> None:
        processor, _loader, mock_repo, mock_extractor, mock_anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.return_value = "text"
        mock_anonymizer.anonymize.side_effect = AnonymizationError("anon failed")

        with pytest.raises(AnonymizationError, match="anon failed"):
            processor.process(uploaded_document_id=1, job_id=1)

    def test_does_not_anonymize_when_extraction_fails(self) -> None:
        processor, _loader, mock_repo, mock_extractor, mock_anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.side_effect = PdfExtractionError("bad pdf")

        with pytest.raises(PdfExtractionError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_anonymizer.anonymize.assert_not_called()

    def test_does_not_persist_anonymised_when_anonymization_fails(self) -> None:
        processor, _loader, mock_repo, mock_extractor, mock_anonymizer = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.return_value = "text"
        mock_anonymizer.anonymize.side_effect = AnonymizationError("boom")

        with pytest.raises(AnonymizationError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_repo.update_anonymised_result.assert_not_called()


class TestProcessPropagatesErrors:
    def test_propagates_document_not_found(self) -> None:
        processor, _loader, mock_repo, _extractor, _anonymizer = _make_processor()
        mock_repo.find_by_id.side_effect = DocumentNotFoundError("Document 99 not found")

        with pytest.raises(DocumentNotFoundError, match="99"):
            processor.process(uploaded_document_id=99, job_id=1)

    def test_does_not_call_loader_when_document_missing(self) -> None:
        processor, mock_loader, mock_repo, _extractor, _anonymizer = _make_processor()
        mock_repo.find_by_id.side_effect = DocumentNotFoundError("not found")

        with pytest.raises(DocumentNotFoundError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_loader.load.assert_not_called()
