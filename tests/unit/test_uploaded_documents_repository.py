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


def _mock_connection(mock_get_conn: MagicMock) -> tuple[MagicMock, MagicMock]:
    """Wire up a mock connection + cursor and return (mock_conn, mock_cursor)."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


class TestFindById:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_returns_uploaded_document_when_found(self, mock_get_conn: MagicMock) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.fetchone.return_value = _make_row()

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
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.fetchone.return_value = None

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match="Document 999 not found"):
            repo.find_by_id(999)


class TestGetSensitiveWords:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_returns_words_when_found(self, mock_get_conn: MagicMock) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.fetchone.return_value = ("ivan petrenko",)

        repo = UploadedDocumentsRepository()
        result = repo.get_sensitive_words(10)

        assert result == ["ivan", "petrenko"]

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_returns_empty_list_when_user_not_found(self, mock_get_conn: MagicMock) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.fetchone.return_value = None

        repo = UploadedDocumentsRepository()
        result = repo.get_sensitive_words(999)

        assert result == []

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_returns_empty_list_when_dictionary_is_null(self, mock_get_conn: MagicMock) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.fetchone.return_value = (None,)

        repo = UploadedDocumentsRepository()
        result = repo.get_sensitive_words(10)

        assert result == []

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_lowercases_dictionary_words(self, mock_get_conn: MagicMock) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.fetchone.return_value = ("Ivan PETRENKO",)

        repo = UploadedDocumentsRepository()
        result = repo.get_sensitive_words(10)

        assert result == ["ivan", "petrenko"]

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_executes_correct_query(self, mock_get_conn: MagicMock) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.fetchone.return_value = ("word",)

        repo = UploadedDocumentsRepository()
        repo.get_sensitive_words(42)

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args.args
        assert "accounts" in sql
        assert "sensitive_words" in sql
        assert params == (42,)


class TestUpdateParsedResult:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_executes_update_query(self, mock_get_conn: MagicMock) -> None:
        _mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_parsed_result(42, "extracted text")

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args.args
        assert "UPDATE uploaded_documents" in sql
        assert "parsed_result" in sql
        assert params == ("extracted text", 42)

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_commits_transaction(self, mock_get_conn: MagicMock) -> None:
        mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_parsed_result(1, "text")

        mock_conn.commit.assert_called_once()

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_document_not_found_when_no_rows_updated(
        self, mock_get_conn: MagicMock
    ) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 0

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match="Document 999 not found"):
            repo.update_parsed_result(999, "text")


class TestUpdateAnonymisedResult:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_executes_update_query(self, mock_get_conn: MagicMock) -> None:
        _mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1
        artifacts = [{"type": "PERSON", "original": "John", "replacement": "PERSON_1"}]

        repo = UploadedDocumentsRepository()
        repo.update_anonymised_result(42, "anon text", artifacts)

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args.args
        assert "UPDATE uploaded_documents" in sql
        assert "anonymised_result" in sql
        assert "anonymised_artifacts" in sql
        assert "transliteration_mapping" in sql
        assert params[0] == "anon text"
        assert params[3] == 42

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_passes_transliteration_mapping(self, mock_get_conn: MagicMock) -> None:
        _mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_anonymised_result(1, "text", [], transliteration_mapping=[0, 1, 2])

        sql, params = mock_cursor.execute.call_args.args
        assert "transliteration_mapping" in sql
        assert params[2] is not None

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_commits_transaction(self, mock_get_conn: MagicMock) -> None:
        mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_anonymised_result(1, "text", [])

        mock_conn.commit.assert_called_once()

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_document_not_found_when_no_rows_updated(
        self, mock_get_conn: MagicMock
    ) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 0

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match="Document 999 not found"):
            repo.update_anonymised_result(999, "text", [])
