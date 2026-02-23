from unittest.mock import MagicMock

import pytest

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


def _make_processor() -> tuple[Processor, MagicMock, MagicMock, MagicMock]:
    mock_file_loader = MagicMock()
    mock_doc_repo = MagicMock()
    mock_pdf_extractor = MagicMock()
    processor = Processor(
        file_loader=mock_file_loader,
        doc_repo=mock_doc_repo,
        pdf_extractor=mock_pdf_extractor,
    )
    return processor, mock_file_loader, mock_doc_repo, mock_pdf_extractor


class TestProcessStep1:
    def test_calls_find_by_id_with_document_id(self) -> None:
        processor, _loader, mock_repo, _extractor = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=42, job_id=1)

        mock_repo.find_by_id.assert_called_once_with(42)

    def test_calls_file_loader_with_document(self) -> None:
        processor, mock_loader, mock_repo, _extractor = _make_processor()
        document = _make_document()
        mock_repo.find_by_id.return_value = document

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_loader.load.assert_called_once_with(document)


class TestProcessStep2:
    def test_calls_pdf_extractor_with_raw_bytes(self) -> None:
        processor, mock_loader, mock_repo, mock_extractor = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_loader.load.return_value = b"%PDF-fake"
        mock_extractor.extract.return_value = "extracted text"

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_extractor.extract.assert_called_once_with(b"%PDF-fake")

    def test_persists_extracted_text(self) -> None:
        processor, mock_loader, mock_repo, mock_extractor = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_loader.load.return_value = b"%PDF-fake"
        mock_extractor.extract.return_value = "extracted text"

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=7, job_id=1)

        mock_repo.update_parsed_result.assert_called_once_with(7, "extracted text")

    def test_calls_steps_in_order(self) -> None:
        """find_by_id -> load -> extract -> update_parsed_result."""
        processor, mock_loader, mock_repo, mock_extractor = _make_processor()
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

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        assert call_order == ["find_by_id", "load", "extract", "update_parsed_result"]

    def test_raises_not_implemented_after_step2(self) -> None:
        processor, _loader, mock_repo, mock_extractor = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.return_value = "text"

        with pytest.raises(NotImplementedError, match="Steps 3"):
            processor.process(uploaded_document_id=1, job_id=1)

    def test_propagates_pdf_extraction_error(self) -> None:
        processor, _loader, mock_repo, mock_extractor = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.side_effect = PdfExtractionError("bad pdf")

        with pytest.raises(PdfExtractionError, match="bad pdf"):
            processor.process(uploaded_document_id=1, job_id=1)

    def test_does_not_persist_when_extraction_fails(self) -> None:
        processor, _loader, mock_repo, mock_extractor = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()
        mock_extractor.extract.side_effect = PdfExtractionError("bad pdf")

        with pytest.raises(PdfExtractionError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_repo.update_parsed_result.assert_not_called()


class TestProcessPropagatesErrors:
    def test_propagates_document_not_found(self) -> None:
        processor, _loader, mock_repo, _extractor = _make_processor()
        mock_repo.find_by_id.side_effect = DocumentNotFoundError("Document 99 not found")

        with pytest.raises(DocumentNotFoundError, match="99"):
            processor.process(uploaded_document_id=99, job_id=1)

    def test_does_not_call_loader_when_document_missing(self) -> None:
        processor, mock_loader, mock_repo, _extractor = _make_processor()
        mock_repo.find_by_id.side_effect = DocumentNotFoundError("not found")

        with pytest.raises(DocumentNotFoundError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_loader.load.assert_not_called()
