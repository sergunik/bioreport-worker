from psycopg.rows import dict_row

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
