import pytest

from app.database.connection import get_connection
from app.database.models import JobRecord
from app.database.repositories.job_repository import JobRepository


@pytest.mark.integration
class TestJobRepositoryClaimNextJob:
    def test_claim_next_job_returns_and_locks_job(self, seed_job: JobRecord, db_conn) -> None:
        repo = JobRepository(max_attempts=3)
        job = repo.claim_next_job(db_conn)
        assert job is not None
        assert job.id == seed_job.id
        assert job.uploaded_document_id == seed_job.uploaded_document_id
        assert job.status == "processing"
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT status, locked_at FROM pdf_jobs WHERE id = %s",
                (job.id,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "processing"
        assert row[1] is not None

    def test_claim_next_job_returns_none_when_no_pending_jobs(self, db_conn) -> None:
        repo = JobRepository(max_attempts=3)
        job = repo.claim_next_job(db_conn)
        assert job is None

    def test_claim_next_job_skips_job_with_attempts_at_max(
        self, seed_document: tuple[int, str, int], db_conn, integration_cleanup
    ) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pdf_jobs (uploaded_document_id, status, attempts)
                VALUES (%s, 'pending', 3)
                RETURNING id
                """,
                (seed_document[0],),
            )
            row = cur.fetchone()
            assert row is not None
            job_id = row[0]
        db_conn.commit()
        integration_cleanup.append(("pdf_jobs", job_id))
        repo = JobRepository(max_attempts=3)
        job = repo.claim_next_job(db_conn)
        assert job is None


@pytest.mark.integration
class TestJobRepositoryMarkDone:
    def test_mark_done_updates_status(self, seed_job: JobRecord, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pdf_jobs SET status = 'processing' WHERE id = %s
                """,
                (seed_job.id,),
            )
        db_conn.commit()
        repo = JobRepository(max_attempts=3)
        repo.mark_done(seed_job.id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM pdf_jobs WHERE id = %s",
                    (seed_job.id,),
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == "done"


@pytest.mark.integration
class TestJobRepositoryMarkFailed:
    def test_mark_failed_updates_status_and_error_message(
        self, seed_job: JobRecord, db_conn
    ) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pdf_jobs SET status = 'processing' WHERE id = %s
                """,
                (seed_job.id,),
            )
        db_conn.commit()
        repo = JobRepository(max_attempts=3)
        repo.mark_failed(seed_job.id, "error text")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, error_message FROM pdf_jobs WHERE id = %s",
                    (seed_job.id,),
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == "failed"
        assert row[1] == "error text"


@pytest.mark.integration
class TestJobRepositoryIncrementAttempts:
    def test_increment_attempts_returns_to_pending(self, seed_job: JobRecord, db_conn) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pdf_jobs
                SET status = 'processing', attempts = 1, locked_at = NOW()
                WHERE id = %s
                """,
                (seed_job.id,),
            )
        db_conn.commit()
        repo = JobRepository(max_attempts=3)
        repo.increment_attempts(seed_job.id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, attempts, locked_at FROM pdf_jobs WHERE id = %s",
                    (seed_job.id,),
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == "pending"
        assert row[1] == 2
        assert row[2] is None


@pytest.mark.integration
class TestJobRepositoryFindById:
    def test_find_by_id_returns_job(self, seed_job: JobRecord) -> None:
        repo = JobRepository(max_attempts=3)
        job = repo.find_by_id(seed_job.id)
        assert job is not None
        assert job.id == seed_job.id
        assert job.uploaded_document_id == seed_job.uploaded_document_id
        assert job.status == "pending"
        assert job.attempts == 0

    def test_find_by_id_returns_none_when_not_found(self) -> None:
        repo = JobRepository(max_attempts=3)
        assert repo.find_by_id(99999) is None
