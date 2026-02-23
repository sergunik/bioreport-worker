from unittest.mock import MagicMock, patch

import pytest

from app.database.repositories.uploaded_documents_repository import UploadedDocumentsRepository
from app.processor.exceptions import DocumentNotFoundError
from app.processor.models import UploadedDocument


def _make_row() -> dict:
    return {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": 10,
        "storage_disk": "local",
        "file_hash_sha256": "a" * 64,
        "mime_type": "application/pdf",
        "file_size_bytes": 2048,
    }


class TestFindById:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_returns_uploaded_document_when_found(self, mock_get_conn: MagicMock) -> None:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = _make_row()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        repo = UploadedDocumentsRepository()
        result = repo.find_by_id(1)

        assert isinstance(result, UploadedDocument)
        assert result.id == 1
        assert result.uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert result.user_id == 10
        assert result.storage_disk == "local"
        assert result.mime_type == "application/pdf"
        assert result.file_size_bytes == 2048

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_document_not_found_when_missing(self, mock_get_conn: MagicMock) -> None:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match="Document 999 not found"):
            repo.find_by_id(999)
