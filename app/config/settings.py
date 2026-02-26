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

    normalization_provider: str = "openai"

    normalization_openai_api_key: str = ""
    normalization_openai_model_name: str = "gpt-4.1-mini"
    normalization_openai_timeout_seconds: int = 30
    normalization_openai_rate_limit_per_minute: int = 60
    normalization_openai_temperature: float = 0.0

    normalization_openai_compatible_api_key: str = ""
    normalization_openai_compatible_model_name: str = ""
    normalization_openai_compatible_timeout_seconds: int = 30
    normalization_openai_compatible_base_url: str = ""

    normalization_openrouter_api_key: str = ""
    normalization_openrouter_model_name: str = ""
    normalization_openrouter_timeout_seconds: int = 30

    normalization_groq_api_key: str = ""
    normalization_groq_model_name: str = ""
    normalization_groq_timeout_seconds: int = 30

    normalization_together_api_key: str = ""
    normalization_together_model_name: str = ""
    normalization_together_timeout_seconds: int = 30

    normalization_deepseek_api_key: str = ""
    normalization_deepseek_model_name: str = ""
    normalization_deepseek_timeout_seconds: int = 30

    normalization_ollama_api_key: str = ""
    normalization_ollama_model_name: str = ""
    normalization_ollama_timeout_seconds: int = 30
