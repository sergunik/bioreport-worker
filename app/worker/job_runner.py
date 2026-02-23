from app.config.settings import Settings
from app.database.models import JobRecord
from app.database.repositories.job_repository import JobRepository
from app.logging.logger import Log
from app.processor.processor import Processor


class JobRunner:
    """Run one job, catch exceptions, and apply retry logic."""

    def __init__(
        self,
        processor: Processor,
        job_repo: JobRepository,
        settings: Settings,
    ) -> None:
        self._processor = processor
        self._job_repo = job_repo
        self._settings = settings

    def run(self, job: JobRecord) -> None:
        """Execute a single job with error handling."""
        Log.info(f"Running job {job.id} (attempt {job.attempts + 1})")
        try:
            self._processor.process(job.uploaded_document_id, job.id)
            self._job_repo.mark_done(job.id)
            Log.info(f"Job {job.id} completed successfully")
        except Exception as exc:
            self._handle_failure(job, exc)

    def _handle_failure(self, job: JobRecord, exc: Exception) -> None:
        """Increment attempts; mark failed if at max, otherwise back to pending."""
        Log.error(f"Job {job.id} failed: {exc}")
        if job.attempts + 1 >= self._settings.max_job_attempts:
            self._job_repo.mark_failed(job.id, str(exc))
            Log.error(f"Job {job.id} permanently failed after {job.attempts + 1} attempts")
        else:
            self._job_repo.increment_attempts(job.id)
            Log.warning(f"Job {job.id} will be retried (attempt {job.attempts + 1})")
