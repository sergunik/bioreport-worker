from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.database.connection import get_connection
from app.processor.exceptions import DocumentNotFoundError
from app.processor.models import UploadedDocument


class UploadedDocumentsRepository:
    """Database operations for the uploaded_documents table."""

    def find_by_id(self, document_id: int) -> UploadedDocument:
        """Find an uploaded document by ID.

        Raises:
            DocumentNotFoundError: if no document with this ID exists.
        """
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, uuid, user_id, storage_disk, file_size_bytes,
                           mime_type, file_hash_sha256
                    FROM uploaded_documents
                    WHERE id = %s
                    """,
                    (document_id,),
                )
                row = cur.fetchone()

        if row is None:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        return UploadedDocument(
            id=row["id"],
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

    def update_anonymised_result(
        self,
        document_id: int,
        anonymised_result: str,
        artifacts_payload: dict[str, Any],
        transliteration_mapping: list[int] | None = None,
    ) -> None:
        """Persist anonymized text, artifact mappings, and transliteration mapping.

        Args:
            document_id: Target document ID.
            anonymised_result: Anonymized full text.
            artifacts_payload: JSONB-ready dict with 'artifacts' key (list of artifact dicts).
            transliteration_mapping: Optional list of code point mappings.

        Raises:
            DocumentNotFoundError: if no document with this ID exists.
        """
        artifacts = artifacts_payload.get("artifacts")
        if not isinstance(artifacts, list):
            raise ValueError("artifacts_payload must contain an 'artifacts' list")

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
                        anonymised_artifacts = %s,
                        transliteration_mapping = %s
                    WHERE id = %s
                    """,
                    (
                        anonymised_result,
                        Jsonb(artifacts_payload),
                        transliteration_value,
                        document_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise DocumentNotFoundError(f"Document {document_id} not found")
            conn.commit()

    def update_parsed_result(self, document_id: int, parsed_result: str) -> None:
        """Persist extracted text into the parsed_result column.

        Raises:
            DocumentNotFoundError: if no document with this ID exists.
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE uploaded_documents
                    SET parsed_result = %s
                    WHERE id = %s
                    """,
                    (parsed_result, document_id),
                )
                if cur.rowcount == 0:
                    raise DocumentNotFoundError(f"Document {document_id} not found")
            conn.commit()
