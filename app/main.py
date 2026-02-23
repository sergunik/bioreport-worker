from app.config.settings import Settings
from app.database.connection import close_pool, init_pool
from app.database.repositories.job_repository import JobRepository
from app.logging.logger import Log
from app.processor.processor import build_processor
from app.worker.job_runner import JobRunner
from app.worker.worker import Worker


def main() -> None:
    """Entry point: initialize pool -> build dependencies -> start worker loop."""
    settings = Settings()
    Log.configure(settings.log_level)
    init_pool(settings)

    try:
        processor = build_processor(settings)
        job_repo = JobRepository(settings.max_job_attempts)
        job_runner = JobRunner(processor, job_repo, settings)
        worker = Worker(job_repo, job_runner, settings)
        worker.run()
    finally:
        close_pool()


if __name__ == "__main__":
    main()
