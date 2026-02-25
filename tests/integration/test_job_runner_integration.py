from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("icu")

from app.config.settings import Settings
from app.database.connection import get_connection
from app.database.models import JobRecord
from app.database.repositories.job_repository import JobRepository
from app.processor.processor import Processor, build_processor
from app.worker.job_runner import JobRunner


@pytest.mark.integration
class TestJobRunnerSuccess:
    def test_run_marks_job_done(
        self,
        sample_pdf_on_disk: tuple[int, str, object],
        seed_job: JobRecord,
        test_settings: Settings,
    ) -> None:
        document_id, _doc_uuid, files_root = sample_pdf_on_disk
        job = JobRecord(
            id=seed_job.id,
            uploaded_document_id=document_id,
            status="pending",
            attempts=0,
        )
        processor = build_processor(test_settings, files_root=files_root)
        original_process = processor.process

        def process_without_raise(uid: int, jid: int) -> None:
            try:
                original_process(uid, jid)
            except NotImplementedError:
                pass

        with patch.object(processor, "process", process_without_raise):
            job_repo = JobRepository(max_attempts=test_settings.max_job_attempts)
            runner = JobRunner(processor, job_repo, test_settings)
            runner.run(job)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM pdf_jobs WHERE id = %s",
                    (job.id,),
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == "done"


@pytest.mark.integration
class TestJobRunnerRetry:
    def test_run_increments_attempts_on_failure(
        self,
        seed_job: JobRecord,
        test_settings: Settings,
    ) -> None:
        mock_processor = MagicMock(spec=Processor)
        mock_processor.process.side_effect = Exception("boom")
        job_repo = JobRepository(max_attempts=test_settings.max_job_attempts)
        runner = JobRunner(mock_processor, job_repo, test_settings)
        runner.run(seed_job)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, attempts FROM pdf_jobs WHERE id = %s",
                    (seed_job.id,),
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == "pending"
        assert row[1] == 1

    def test_run_marks_failed_after_max_attempts(
        self,
        seed_job: JobRecord,
        test_settings: Settings,
        db_conn,
    ) -> None:
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE pdf_jobs SET attempts = 2 WHERE id = %s",
                (seed_job.id,),
            )
        db_conn.commit()
        job = JobRecord(
            id=seed_job.id,
            uploaded_document_id=seed_job.uploaded_document_id,
            status="processing",
            attempts=2,
        )
        processor = MagicMock(spec=Processor)
        processor.process.side_effect = Exception("boom")
        job_repo = JobRepository(max_attempts=test_settings.max_job_attempts)
        runner = JobRunner(processor, job_repo, test_settings)
        runner.run(job)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, error_message FROM pdf_jobs WHERE id = %s",
                    (seed_job.id,),
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == "failed"
        assert row[1] == "boom"
