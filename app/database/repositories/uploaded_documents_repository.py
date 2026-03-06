from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.database.connection import get_connection
from app.processor.exceptions import DocumentNotFoundError
from app.processor.models import UploadedDocument


class UploadedDocumentsRepository:
    """Database operations for the uploaded_documents table."""

    def find_by_uuid(self, document_uuid: str) -> UploadedDocument:
        """Find an uploaded document by UUID.

        Raises:
            DocumentNotFoundError: if no document with this UUID exists.
        """
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT uuid, user_id, storage_disk, file_size_bytes,
                           mime_type, file_hash_sha256
                    FROM uploaded_documents
                    WHERE uuid = %s::uuid
                    """,
                    (document_uuid,),
                )
                row = cur.fetchone()

        if row is None:
            raise DocumentNotFoundError(f"Document {document_uuid} not found")

        return UploadedDocument(
            id=row.get("id", 0),
            uuid=str(row["uuid"]),
            user_id=row["user_id"],
            storage_disk=row["storage_disk"],
            file_hash_sha256=row["file_hash_sha256"],
            mime_type=row["mime_type"],
            file_size_bytes=row["file_size_bytes"],
        )

    def get_sensitive_words(self, user_id: int) -> list[str]:
        """Fetch sensitive words for a user from the accounts table.

        Returns lowercase tokens. Empty list if user has no dictionary.
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT sensitive_words FROM accounts WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()

        if row is None or row[0] is None:
            return []

        raw: str = row[0]
        return raw.lower().split()

    def update_anonymized_text(
        self,
        document_uuid: str,
        anonymized_result: str,
        transliteration_mapping: list[int] | None = None,
    ) -> None:
        """Persist anonymized text and transliteration mapping."""
        transliteration_value = (
            Jsonb(transliteration_mapping)
            if transliteration_mapping is not None
            else None
        )
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE uploaded_documents
                    SET anonymised_result = %s,
                        transliteration_mapping = %s
                    WHERE uuid = %s::uuid
                    """,
                    (
                        anonymized_result,
                        transliteration_value,
                        document_uuid,
                    ),
                )
                if cur.rowcount == 0:
                    raise DocumentNotFoundError(f"Document {document_uuid} not found")
            conn.commit()

    def update_artifacts_payload(
        self,
        document_uuid: str,
        artifacts_payload: dict[str, Any],
    ) -> None:
        """Persist anonymization artifacts payload."""
        artifacts = artifacts_payload.get("artifacts")
        if not isinstance(artifacts, list):
            raise ValueError("artifacts_payload must contain an 'artifacts' list")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE uploaded_documents
                    SET anonymised_artifacts = %s
                    WHERE uuid = %s::uuid
                    """,
                    (Jsonb(artifacts_payload), document_uuid),
                )
                if cur.rowcount == 0:
                    raise DocumentNotFoundError(f"Document {document_uuid} not found")
            conn.commit()

    def update_parsed_result(self, document_uuid: str, parsed_result: str) -> None:
        """Persist extracted text into the parsed_result column.

        Raises:
            DocumentNotFoundError: if no document with this UUID exists.
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE uploaded_documents
                    SET parsed_result = %s
                    WHERE uuid = %s::uuid
                    """,
                    (parsed_result, document_uuid),
                )
                if cur.rowcount == 0:
                    raise DocumentNotFoundError(f"Document {document_uuid} not found")
            conn.commit()

    def update_normalized_result(
        self,
        document_uuid: str,
        normalized_result: dict[str, Any],
    ) -> None:
        """Persist raw normalized JSON as returned by the AI provider.

        Raises:
            DocumentNotFoundError: if no document with this UUID exists.
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE uploaded_documents
                    SET normalized_result = %s
                    WHERE uuid = %s::uuid
                    """,
                    (Jsonb(normalized_result), document_uuid),
                )
                if cur.rowcount == 0:
                    raise DocumentNotFoundError(f"Document {document_uuid} not found")
            conn.commit()

    def update_final_result(
        self,
        document_uuid: str,
        final_result: dict[str, Any],
    ) -> None:
        """Persist de-anonymized final JSON output and mark processing complete.

        Raises:
            DocumentNotFoundError: if no document with this UUID exists.
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE uploaded_documents
                    SET final_result = %s,
                        processed_at = NOW()
                    WHERE uuid = %s::uuid
                    """,
                    (Jsonb(final_result), document_uuid),
                )
                if cur.rowcount == 0:
                    raise DocumentNotFoundError(f"Document {document_uuid} not found")
            conn.commit()
