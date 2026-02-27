import pytest
from pydantic import ValidationError

from app.config.settings import Settings


class TestSettingsDefaults:
    def test_default_app_env(self) -> None:
        s = Settings()
        assert s.app_env == "dev"

#     def test_default_log_level(self) -> None:
#         s = Settings()
#         assert s.log_level == "INFO"

    def test_default_db_port(self) -> None:
        s = Settings()
        assert s.db_port == 5432

    def test_default_max_job_attempts(self) -> None:
        s = Settings()
        assert s.max_job_attempts == 3

    def test_default_job_poll_interval(self) -> None:
        s = Settings()
        assert s.job_poll_interval_seconds == 5

    def test_default_pdf_engine(self) -> None:
        s = Settings()
        assert s.pdf_engine == "pdfplumber"

    def test_default_normalization_provider(self) -> None:
        s = Settings()
        assert s.normalization_provider == "openai"

    def test_default_normalization_openai_timeout(self) -> None:
        s = Settings()
        assert s.normalization_openai_timeout_seconds == 30


class TestSettingsFromEnv:
    def test_loads_app_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        s = Settings()
        assert s.app_env == "production"

    def test_loads_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.log_level == "DEBUG"

    def test_loads_db_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_HOST", "db.example.com")
        s = Settings()
        assert s.db_host == "db.example.com"

    def test_loads_db_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_PORT", "5433")
        s = Settings()
        assert s.db_port == 5433

    def test_loads_max_job_attempts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAX_JOB_ATTEMPTS", "5")
        s = Settings()
        assert s.max_job_attempts == 5


class TestSettingsValidation:
    def test_invalid_db_port_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_PORT", "not_a_number")
        with pytest.raises(ValidationError):
            Settings()

    def test_invalid_max_attempts_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAX_JOB_ATTEMPTS", "abc")
        with pytest.raises(ValidationError):
            Settings()
