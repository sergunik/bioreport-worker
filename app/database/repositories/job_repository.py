from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.database.connection import get_connection
from app.database.models import JobRecord


class JobRepository:
    """Database operations for the pdf_jobs table."""

    def __init__(self, max_attempts: int) -> None:
        self._max_attempts = max_attempts

    def claim_next_job(self, conn: psycopg.Connection[Any]) -> JobRecord | None:
        """Claim the next pending job using SELECT FOR UPDATE SKIP LOCKED."""
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, uploaded_document_id, status, attempts
                FROM pdf_jobs
                WHERE status = 'pending'
                  AND attempts < %s
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                (self._max_attempts,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        conn.execute(
            """
            UPDATE pdf_jobs
            SET status = 'processing', locked_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """,
            (row["id"],),
        )
        conn.commit()

        return JobRecord(
            id=row["id"],
            uploaded_document_id=row["uploaded_document_id"],
            status="processing",
            attempts=row["attempts"],
        )

    def mark_done(self, job_id: int) -> None:
        """Mark a job as done."""
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE pdf_jobs
                SET status = 'done', updated_at = NOW()
                WHERE id = %s
                """,
                (job_id,),
            )
            conn.commit()

    def mark_failed(self, job_id: int, error: str) -> None:
        """Mark a job as permanently failed."""
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE pdf_jobs
                SET status = 'failed', error_message = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (error, job_id),
            )
            conn.commit()

    def increment_attempts(self, job_id: int) -> None:
        """Increment attempt count and return job to pending."""
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE pdf_jobs
                SET attempts = attempts + 1, status = 'pending',
                    locked_at = NULL, updated_at = NOW()
                WHERE id = %s
                """,
                (job_id,),
            )
            conn.commit()

    def find_by_id(self, job_id: int) -> JobRecord | None:
        """Find a job by ID. Useful for tests."""
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, uploaded_document_id, status, attempts,
                           error_message, locked_at, created_at, updated_at
                    FROM pdf_jobs
                    WHERE id = %s
                    """,
                    (job_id,),
                )
                row = cur.fetchone()

        if row is None:
            return None

        return JobRecord(
            id=row["id"],
            uploaded_document_id=row["uploaded_document_id"],
            status=row["status"],
            attempts=row["attempts"],
            error_message=row["error_message"],
            locked_at=row["locked_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
