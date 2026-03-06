from unittest.mock import MagicMock, patch

import pytest

from app.database.repositories.uploaded_documents_repository import UploadedDocumentsRepository
from app.processor.exceptions import DocumentNotFoundError
from app.processor.models import UploadedDocument

NIL_UUID = "00000000-0000-0000-0000-000000000000"


def _make_row() -> dict:
    return {
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


class TestFindByUuid:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_returns_uploaded_document_when_found(self, mock_get_conn: MagicMock) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.fetchone.return_value = _make_row()
        doc_uuid = "550e8400-e29b-41d4-a716-446655440000"

        repo = UploadedDocumentsRepository()
        result = repo.find_by_uuid(doc_uuid)

        assert isinstance(result, UploadedDocument)
        assert result.uuid == doc_uuid
        assert result.user_id == 10
        assert result.storage_disk == "local"
        assert result.mime_type == "application/pdf"
        assert result.file_size_bytes == 2048

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_document_not_found_when_missing(self, mock_get_conn: MagicMock) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.fetchone.return_value = None

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match=f"Document {NIL_UUID} not found"):
            repo.find_by_uuid(NIL_UUID)


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
        doc_uuid = "550e8400-e29b-41d4-a716-446655440000"

        repo = UploadedDocumentsRepository()
        repo.update_parsed_result(doc_uuid, "extracted text")

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args.args
        assert "UPDATE uploaded_documents" in sql
        assert "parsed_result" in sql
        assert params == ("extracted text", doc_uuid)

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_commits_transaction(self, mock_get_conn: MagicMock) -> None:
        mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_parsed_result("550e8400-e29b-41d4-a716-446655440000", "text")

        mock_conn.commit.assert_called_once()

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_document_not_found_when_no_rows_updated(
        self, mock_get_conn: MagicMock
    ) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 0

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match=f"Document {NIL_UUID} not found"):
            repo.update_parsed_result(NIL_UUID, "text")


class TestUpdateAnonymizedText:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_executes_update_query(self, mock_get_conn: MagicMock) -> None:
        _mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1
        doc_uuid = "550e8400-e29b-41d4-a716-446655440000"

        repo = UploadedDocumentsRepository()
        repo.update_anonymized_text(
            doc_uuid,
            anonymized_result="anon text",
            transliteration_mapping=[0, 1, 2],
        )

        mock_cursor.execute.assert_called_once()
        sql, _params = mock_cursor.execute.call_args.args
        assert "UPDATE uploaded_documents" in sql
        assert "anonymised_result" in sql
        assert "transliteration_mapping" in sql

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_stores_null_when_transliteration_mapping_is_none(
        self, mock_get_conn: MagicMock
    ) -> None:
        _mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_anonymized_text(
            "550e8400-e29b-41d4-a716-446655440000",
            anonymized_result="text",
            transliteration_mapping=None,
        )

        _sql, params = mock_cursor.execute.call_args.args
        assert params[1] is None  # transliteration_mapping

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_commits_transaction(self, mock_get_conn: MagicMock) -> None:
        mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_anonymized_text(
            "550e8400-e29b-41d4-a716-446655440000",
            anonymized_result="text",
        )

        mock_conn.commit.assert_called_once()

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_document_not_found_when_no_rows_updated(
        self, mock_get_conn: MagicMock
    ) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 0

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match=f"Document {NIL_UUID} not found"):
            repo.update_anonymized_text(NIL_UUID, anonymized_result="text")


class TestUpdateArtifactsPayload:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_executes_update_query(self, mock_get_conn: MagicMock) -> None:
        _mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1
        doc_uuid = "550e8400-e29b-41d4-a716-446655440000"

        repo = UploadedDocumentsRepository()
        repo.update_artifacts_payload(doc_uuid, artifacts_payload={"artifacts": []})

        mock_cursor.execute.assert_called_once()
        sql, _params = mock_cursor.execute.call_args.args
        assert "UPDATE uploaded_documents" in sql
        assert "anonymised_artifacts" in sql

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_when_artifacts_not_list(self, mock_get_conn: MagicMock) -> None:
        _mock_conn, mock_cursor = _mock_connection(mock_get_conn)

        repo = UploadedDocumentsRepository()

        with pytest.raises(ValueError, match="artifacts"):
            repo.update_artifacts_payload(
                "550e8400-e29b-41d4-a716-446655440000",
                artifacts_payload={"artifacts": "not a list"},
            )

        mock_cursor.execute.assert_not_called()

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_commits_transaction(self, mock_get_conn: MagicMock) -> None:
        mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_artifacts_payload(
            "550e8400-e29b-41d4-a716-446655440000", artifacts_payload={"artifacts": []}
        )

        mock_conn.commit.assert_called_once()

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_document_not_found_when_no_rows_updated(
        self, mock_get_conn: MagicMock
    ) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 0

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match=f"Document {NIL_UUID} not found"):
            repo.update_artifacts_payload(NIL_UUID, artifacts_payload={"artifacts": []})


class TestUpdateNormalizedResult:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_executes_update_query(self, mock_get_conn: MagicMock) -> None:
        _mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1
        doc_uuid = "550e8400-e29b-41d4-a716-446655440000"

        repo = UploadedDocumentsRepository()
        repo.update_normalized_result(doc_uuid, normalized_result={"person": {"name": "P1"}})

        mock_cursor.execute.assert_called_once()
        sql, _params = mock_cursor.execute.call_args.args
        assert "UPDATE uploaded_documents" in sql
        assert "normalized_result" in sql

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_commits_transaction(self, mock_get_conn: MagicMock) -> None:
        mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_normalized_result("550e8400-e29b-41d4-a716-446655440000", normalized_result={})

        mock_conn.commit.assert_called_once()

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_document_not_found_when_no_rows_updated(
        self, mock_get_conn: MagicMock
    ) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 0

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match=f"Document {NIL_UUID} not found"):
            repo.update_normalized_result(NIL_UUID, normalized_result={})


class TestUpdateFinalResult:
    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_executes_update_query(self, mock_get_conn: MagicMock) -> None:
        _mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1
        doc_uuid = "550e8400-e29b-41d4-a716-446655440000"

        repo = UploadedDocumentsRepository()
        repo.update_final_result(doc_uuid, final_result={"person": {"name": "John"}})

        mock_cursor.execute.assert_called_once()
        sql, _params = mock_cursor.execute.call_args.args
        assert "UPDATE uploaded_documents" in sql
        assert "final_result" in sql

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_commits_transaction(self, mock_get_conn: MagicMock) -> None:
        mock_conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 1

        repo = UploadedDocumentsRepository()
        repo.update_final_result("550e8400-e29b-41d4-a716-446655440000", final_result={})

        mock_conn.commit.assert_called_once()

    @patch("app.database.repositories.uploaded_documents_repository.get_connection")
    def test_raises_document_not_found_when_no_rows_updated(
        self, mock_get_conn: MagicMock
    ) -> None:
        _conn, mock_cursor = _mock_connection(mock_get_conn)
        mock_cursor.rowcount = 0

        repo = UploadedDocumentsRepository()

        with pytest.raises(DocumentNotFoundError, match=f"Document {NIL_UUID} not found"):
            repo.update_final_result(NIL_UUID, final_result={})
