import pytest

from app.database.repositories.uploaded_documents_repository import UploadedDocumentsRepository
from app.processor.exceptions import DocumentNotFoundError


@pytest.mark.integration
class TestUploadedDocumentsRepositoryFindById:
    def test_find_by_id_returns_document(self, seed_document: tuple[int, str]) -> None:
        document_id, doc_uuid = seed_document
        repo = UploadedDocumentsRepository()
        doc = repo.find_by_id(document_id)
        assert doc.id == document_id
        assert doc.uuid == doc_uuid
        assert doc.user_id == 1
        assert doc.storage_disk == "local"
        assert doc.file_hash_sha256 == "a" * 64
        assert doc.mime_type == "application/pdf"
        assert doc.file_size_bytes == 1024

    def test_find_by_id_raises_when_not_found(self) -> None:
        repo = UploadedDocumentsRepository()
        with pytest.raises(DocumentNotFoundError, match="99999 not found"):
            repo.find_by_id(99999)


@pytest.mark.integration
class TestUploadedDocumentsRepositoryGetSensitiveWords:
    def test_get_sensitive_words_returns_empty_when_no_account(self) -> None:
        repo = UploadedDocumentsRepository()
        assert repo.get_sensitive_words(99999) == []

    def test_get_sensitive_words_returns_words(self, seed_account_with_words: int) -> None:
        repo = UploadedDocumentsRepository()
        words = repo.get_sensitive_words(seed_account_with_words)
        assert words == ["word1", "word2"]


@pytest.mark.integration
class TestUploadedDocumentsRepositoryUpdateParsedResult:
    def test_update_parsed_result_persists(self, seed_document: tuple[int, str], db_conn) -> None:
        document_id, _ = seed_document
        repo = UploadedDocumentsRepository()
        repo.update_parsed_result(document_id, "extracted text")
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT parsed_result FROM uploaded_documents WHERE id = %s",
                (document_id,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "extracted text"

    def test_update_parsed_result_raises_when_not_found(self) -> None:
        repo = UploadedDocumentsRepository()
        with pytest.raises(DocumentNotFoundError):
            repo.update_parsed_result(99999, "x")


@pytest.mark.integration
class TestUploadedDocumentsRepositoryUpdateAnonymisedResult:
    def test_update_anonymised_result_persists_all_fields(
        self, seed_document: tuple[int, str], db_conn
    ) -> None:
        document_id, _ = seed_document
        repo = UploadedDocumentsRepository()
        repo.update_anonymised_result(
            document_id,
            "anon text",
            {"artifacts": [{"type": "name", "value": "X"}]},
            transliteration_mapping=[0, 1, 2],
        )
        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT anonymised_result, anonymised_artifacts, transliteration_mapping
                FROM uploaded_documents WHERE id = %s
                """,
                (document_id,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "anon text"
        assert row[1] == {"artifacts": [{"type": "name", "value": "X"}]}
        assert row[2] == [0, 1, 2]

    def test_update_anonymised_result_raises_when_not_found(self) -> None:
        repo = UploadedDocumentsRepository()
        with pytest.raises(DocumentNotFoundError):
            repo.update_anonymised_result(
                99999, "x", {"artifacts": []}, transliteration_mapping=None
            )
