from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"

    db_host: str = "host.docker.internal"
    db_port: int = 5432
    db_database: str = "bioreport"
    db_username: str = "bioreport"
    db_password: str = "secret"

    max_job_attempts: int = 3
    job_poll_interval_seconds: int = 5

    pdf_engine: str = "pdfplumber"

    openai_api_key: str = ""
    openai_model_name: str = ""
    openai_timeout_seconds: int = 30
    openai_rate_limit_per_minute: int = 60
