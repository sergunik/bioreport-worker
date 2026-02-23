from unittest.mock import MagicMock, patch

from app.database.models import JobRecord
from app.worker.worker import Worker


def _make_worker() -> tuple[Worker, MagicMock, MagicMock]:
    """Create a Worker with mocked dependencies."""
    mock_repo = MagicMock()
    mock_runner = MagicMock()
    settings = MagicMock(job_poll_interval_seconds=1)
    worker = Worker(mock_repo, mock_runner, settings)
    return worker, mock_repo, mock_runner


def _make_job(job_id: int = 1) -> JobRecord:
    return JobRecord(id=job_id, uploaded_document_id=10, status="processing", attempts=0)


class TestWorkerDispatch:
    def test_dispatches_job_to_runner(self) -> None:
        worker, _repo, mock_runner = _make_worker()
        job = _make_job()

        with patch.object(
            worker, "_try_claim_job", side_effect=[job, KeyboardInterrupt]
        ):
            worker.run()

        mock_runner.run.assert_called_once_with(job)

    def test_dispatches_multiple_jobs(self) -> None:
        worker, _repo, mock_runner = _make_worker()
        job1 = _make_job(1)
        job2 = _make_job(2)

        with patch.object(
            worker, "_try_claim_job", side_effect=[job1, job2, KeyboardInterrupt]
        ):
            worker.run()

        assert mock_runner.run.call_count == 2


class TestWorkerSleep:
    def test_sleeps_when_no_job(self) -> None:
        worker, _repo, _runner = _make_worker()

        with (
            patch.object(
                worker, "_try_claim_job", side_effect=[None, KeyboardInterrupt]
            ),
            patch("app.worker.worker.time.sleep") as mock_sleep,
        ):
            worker.run()

        mock_sleep.assert_called_once_with(1)


class TestWorkerShutdown:
    def test_handles_keyboard_interrupt(self) -> None:
        worker, _repo, _runner = _make_worker()

        with patch.object(
            worker, "_try_claim_job", side_effect=KeyboardInterrupt
        ):
            worker.run()  # Should not raise
