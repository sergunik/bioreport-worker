import pytest

pytest.importorskip("icu")

from app.config.settings import Settings
from app.database.connection import get_connection
from app.database.repositories.job_repository import JobRepository
from app.processor.processor import build_processor
from app.worker.job_runner import JobRunner
from app.worker.worker import Worker


@pytest.mark.integration
class TestWorkerIntegration:
    def test_worker_claims_and_completes_one_job(
        self,
        sample_pdf_on_disk: tuple[int, str, object],
        seed_job,
        test_settings: Settings,
    ) -> None:
        _document_id, _doc_uuid, files_root = sample_pdf_on_disk
        processor = build_processor(test_settings, files_root=files_root)
        job_repo = JobRepository(max_attempts=test_settings.max_job_attempts)
        job_runner = JobRunner(processor, job_repo, test_settings)
        worker = Worker(job_repo, job_runner, test_settings)
        worker.run(max_jobs=1)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM pdf_jobs WHERE id = %s",
                    (seed_job.id,),
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == "done"
