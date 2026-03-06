import pytest

from app.database.repositories.uploaded_documents_repository import UploadedDocumentsRepository
from app.processor.exceptions import DocumentNotFoundError

NIL_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.integration
class TestUploadedDocumentsRepositoryFindByUuid:
    def test_find_by_uuid_returns_document(self, seed_document: tuple[int, str, int]) -> None:
        _doc_id, doc_uuid, user_id = seed_document
        repo = UploadedDocumentsRepository()
        doc = repo.find_by_uuid(doc_uuid)
        assert doc.uuid == doc_uuid
        assert doc.user_id == user_id
        assert doc.storage_disk == "local"
        assert doc.file_hash_sha256 == "a" * 64
        assert doc.mime_type == "application/pdf"
        assert doc.file_size_bytes == 1024

    def test_find_by_uuid_raises_when_not_found(self) -> None:
        repo = UploadedDocumentsRepository()
        with pytest.raises(DocumentNotFoundError, match=f"{NIL_UUID} not found"):
            repo.find_by_uuid(NIL_UUID)


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
    def test_update_parsed_result_persists(
        self, seed_document: tuple[int, str, int], db_conn
    ) -> None:
        _doc_id, doc_uuid, _ = seed_document
        repo = UploadedDocumentsRepository()
        repo.update_parsed_result(doc_uuid, "extracted text")
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT parsed_result FROM uploaded_documents WHERE uuid = %s::uuid",
                (doc_uuid,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "extracted text"

    def test_update_parsed_result_raises_when_not_found(self) -> None:
        repo = UploadedDocumentsRepository()
        with pytest.raises(DocumentNotFoundError):
            repo.update_parsed_result(NIL_UUID, "x")


@pytest.mark.integration
class TestUploadedDocumentsRepositoryUpdateAnonymized:
    def test_update_anonymized_text_and_artifacts_persist_all_fields(
        self, seed_document: tuple[int, str, int], db_conn
    ) -> None:
        _doc_id, doc_uuid, _ = seed_document
        repo = UploadedDocumentsRepository()
        repo.update_anonymized_text(
            doc_uuid,
            anonymized_result="anon text",
            transliteration_mapping=[0, 1, 2],
        )
        repo.update_artifacts_payload(
            doc_uuid,
            artifacts_payload={"artifacts": [{"type": "name", "value": "X"}]},
        )
        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT anonymised_result, anonymised_artifacts, transliteration_mapping
                FROM uploaded_documents WHERE uuid = %s::uuid
                """,
                (doc_uuid,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "anon text"
        assert row[1] == {"artifacts": [{"type": "name", "value": "X"}]}
        assert row[2] == [0, 1, 2]

    def test_update_anonymized_text_raises_when_not_found(self) -> None:
        repo = UploadedDocumentsRepository()
        with pytest.raises(DocumentNotFoundError):
            repo.update_anonymized_text(NIL_UUID, "x", transliteration_mapping=None)

    def test_update_artifacts_payload_raises_when_not_found(self) -> None:
        repo = UploadedDocumentsRepository()
        with pytest.raises(DocumentNotFoundError):
            repo.update_artifacts_payload(NIL_UUID, {"artifacts": []})

    def test_update_artifacts_payload_rejects_invalid_artifacts(
        self, seed_document: tuple[int, str, int]
    ) -> None:
        _document_id, doc_uuid, _ = seed_document
        repo = UploadedDocumentsRepository()
        with pytest.raises(ValueError, match="artifacts"):
            repo.update_artifacts_payload(
                doc_uuid,
                artifacts_payload={"wrong_key": []},
            )


@pytest.mark.integration
class TestUploadedDocumentsRepositoryUpdateNormalizedResult:
    def test_update_normalized_result_persists(
        self, seed_document: tuple[int, str, int], db_conn
    ) -> None:
        _doc_id, doc_uuid, _ = seed_document
        repo = UploadedDocumentsRepository()
        normalized = {
            "person": {"name": "PERSON_1", "dob": "1990-01-01"},
            "diagnostic_date": "2025-01-10",
            "diagnostic_title": "Blood panel",
            "language": "en",
            "markers": [],
            "pii": [],
        }
        repo.update_normalized_result(doc_uuid, normalized_result=normalized)
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT normalized_result FROM uploaded_documents WHERE uuid = %s::uuid",
                (doc_uuid,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == normalized

    def test_update_normalized_result_raises_when_not_found(self) -> None:
        repo = UploadedDocumentsRepository()
        with pytest.raises(DocumentNotFoundError):
            repo.update_normalized_result(NIL_UUID, normalized_result={})


@pytest.mark.integration
class TestUploadedDocumentsRepositoryUpdateFinalResult:
    def test_update_final_result_persists(
        self, seed_document: tuple[int, str, int], db_conn
    ) -> None:
        _doc_id, doc_uuid, _ = seed_document
        repo = UploadedDocumentsRepository()
        final = {
            "person": {"name": "John Doe", "dob": "1990-01-01"},
            "diagnostic_date": "2025-01-10",
            "diagnostic_title": "Blood panel",
            "language": "en",
            "markers": [],
            "pii": [],
        }
        repo.update_final_result(doc_uuid, final_result=final)
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT final_result, processed_at FROM uploaded_documents WHERE uuid = %s::uuid",
                (doc_uuid,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == final
        assert row[1] is not None

    def test_update_final_result_raises_when_not_found(self) -> None:
        repo = UploadedDocumentsRepository()
        with pytest.raises(DocumentNotFoundError):
            repo.update_final_result(NIL_UUID, final_result={})
