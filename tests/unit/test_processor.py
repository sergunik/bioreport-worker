from unittest.mock import MagicMock

import pytest

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


def _make_processor() -> tuple[Processor, MagicMock, MagicMock]:
    mock_file_loader = MagicMock()
    mock_doc_repo = MagicMock()
    processor = Processor(file_loader=mock_file_loader, doc_repo=mock_doc_repo)
    return processor, mock_file_loader, mock_doc_repo


class TestProcessStep1:
    def test_calls_find_by_id_with_document_id(self) -> None:
        processor, _loader, mock_repo = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=42, job_id=1)

        mock_repo.find_by_id.assert_called_once_with(42)

    def test_calls_file_loader_with_document(self) -> None:
        processor, mock_loader, mock_repo = _make_processor()
        document = _make_document()
        mock_repo.find_by_id.return_value = document

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_loader.load.assert_called_once_with(document)

    def test_calls_steps_in_order(self) -> None:
        """find_by_id is called before load."""
        processor, mock_loader, mock_repo = _make_processor()
        call_order: list[str] = []
        mock_repo.find_by_id.side_effect = lambda *a: (
            call_order.append("find_by_id"),
            _make_document(),
        )[1]
        mock_loader.load.side_effect = lambda *a: (
            call_order.append("load"),
            b"%PDF",
        )[1]

        with pytest.raises(NotImplementedError):
            processor.process(uploaded_document_id=1, job_id=1)

        assert call_order == ["find_by_id", "load"]

    def test_raises_not_implemented_after_step1(self) -> None:
        processor, _loader, mock_repo = _make_processor()
        mock_repo.find_by_id.return_value = _make_document()

        with pytest.raises(NotImplementedError, match="Steps 2"):
            processor.process(uploaded_document_id=1, job_id=1)


class TestProcessPropagatesErrors:
    def test_propagates_document_not_found(self) -> None:
        processor, _loader, mock_repo = _make_processor()
        mock_repo.find_by_id.side_effect = DocumentNotFoundError("Document 99 not found")

        with pytest.raises(DocumentNotFoundError, match="99"):
            processor.process(uploaded_document_id=99, job_id=1)

    def test_does_not_call_loader_when_document_missing(self) -> None:
        processor, mock_loader, mock_repo = _make_processor()
        mock_repo.find_by_id.side_effect = DocumentNotFoundError("not found")

        with pytest.raises(DocumentNotFoundError):
            processor.process(uploaded_document_id=1, job_id=1)

        mock_loader.load.assert_not_called()
