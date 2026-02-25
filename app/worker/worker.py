import time

from app.config.settings import Settings
from app.database.connection import get_connection
from app.database.models import JobRecord
from app.database.repositories.job_repository import JobRepository
from app.logging.logger import Log
from app.worker.job_runner import JobRunner


class Worker:
    """Poll loop: sleep -> claim -> dispatch."""

    def __init__(
        self,
        job_repo: JobRepository,
        job_runner: JobRunner,
        settings: Settings,
    ) -> None:
        self._job_repo = job_repo
        self._job_runner = job_runner
        self._settings = settings

    def run(self, max_jobs: int | None = None) -> None:
        """Main poll loop. Runs forever until interrupted.

        If max_jobs is set, stop after processing that many jobs (for testing).
        """
        Log.info("Worker started, polling for jobs")
        jobs_done = 0
        try:
            while True:
                if max_jobs is not None and jobs_done >= max_jobs:
                    break
                job = self._try_claim_job()
                if job:
                    self._job_runner.run(job)
                    jobs_done += 1
                    if max_jobs is not None and jobs_done >= max_jobs:
                        break
                else:
                    Log.debug("No jobs available, sleeping")
                    time.sleep(self._settings.job_poll_interval_seconds)
        except KeyboardInterrupt:
            Log.info("Worker shutting down gracefully")

    def _try_claim_job(self) -> JobRecord | None:
        """Attempt to claim the next pending job. Gracefully handle DB errors."""
        try:
            with get_connection() as conn:
                return self._job_repo.claim_next_job(conn)
        except Exception as exc:
            Log.warning(f"Database error, will retry: {exc}")
            return None
