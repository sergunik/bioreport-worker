from unittest.mock import MagicMock

from app.database.models import JobRecord
from app.worker.job_runner import JobRunner


def _make_runner(
    max_attempts: int = 3,
) -> tuple[JobRunner, MagicMock, MagicMock]:
    """Create a JobRunner with mocked dependencies."""
    mock_processor = MagicMock()
    mock_repo = MagicMock()
    settings = MagicMock(max_job_attempts=max_attempts)
    runner = JobRunner(mock_processor, mock_repo, settings)
    return runner, mock_processor, mock_repo


def _make_job(attempts: int = 0) -> JobRecord:
    return JobRecord(id=1, uploaded_document_id=10, status="processing", attempts=attempts)


class TestSuccessfulProcessing:
    def test_calls_processor(self) -> None:
        runner, mock_processor, _repo = _make_runner()
        job = _make_job()

        runner.run(job)

        mock_processor.process.assert_called_once_with(10, 1)

    def test_marks_job_done(self) -> None:
        runner, _processor, mock_repo = _make_runner()
        job = _make_job()

        runner.run(job)

        mock_repo.mark_done.assert_called_once_with(1)


class TestFailureBelowMax:
    def test_increments_attempts(self) -> None:
        runner, mock_processor, mock_repo = _make_runner(max_attempts=3)
        mock_processor.process.side_effect = Exception("boom")
        job = _make_job(attempts=0)

        runner.run(job)

        mock_repo.increment_attempts.assert_called_once_with(1)
        mock_repo.mark_failed.assert_not_called()

    def test_does_not_mark_done(self) -> None:
        runner, mock_processor, mock_repo = _make_runner(max_attempts=3)
        mock_processor.process.side_effect = Exception("boom")
        job = _make_job(attempts=1)

        runner.run(job)

        mock_repo.mark_done.assert_not_called()


class TestFailureAtMax:
    def test_marks_failed(self) -> None:
        runner, mock_processor, mock_repo = _make_runner(max_attempts=3)
        mock_processor.process.side_effect = Exception("boom")
        job = _make_job(attempts=2)

        runner.run(job)

        mock_repo.mark_failed.assert_called_once_with(1, "boom")
        mock_repo.increment_attempts.assert_not_called()

    def test_marks_failed_when_over_max(self) -> None:
        runner, mock_processor, mock_repo = _make_runner(max_attempts=3)
        mock_processor.process.side_effect = Exception("boom")
        job = _make_job(attempts=5)

        runner.run(job)

        mock_repo.mark_failed.assert_called_once_with(1, "boom")
