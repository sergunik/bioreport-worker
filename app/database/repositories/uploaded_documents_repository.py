from psycopg.rows import dict_row

from app.database.connection import get_connection
from app.database.models import DocumentRecord


class UploadedDocumentsRepository:
    """Database operations for the uploaded_documents table."""

    def find_by_id(self, document_id: int) -> DocumentRecord | None:
        """Find an uploaded document by ID."""
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, uuid, user_id, storage_disk, file_size_bytes,
                           mime_type, file_hash_sha256, parsed_result,
                           anonymised_result, anonymised_artifacts,
                           normalized_result, processed_at, created_at, updated_at
                    FROM uploaded_documents
                    WHERE id = %s
                    """,
                    (document_id,),
                )
                row = cur.fetchone()

        if row is None:
            return None

        return DocumentRecord(
            id=row["id"],
            uuid=row["uuid"],
            user_id=row["user_id"],
            storage_disk=row["storage_disk"],
            file_size_bytes=row["file_size_bytes"],
            mime_type=row["mime_type"],
            file_hash_sha256=row["file_hash_sha256"],
            parsed_result=row["parsed_result"],
            anonymised_result=row["anonymised_result"],
            anonymised_artifacts=row["anonymised_artifacts"],
            normalized_result=row["normalized_result"],
            processed_at=row["processed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
