from typing import ClassVar

from app.config.settings import Settings
from app.normalization.base import BaseNormalizer
from app.normalization.example_client_adapter import ExampleClientAdapter
from app.normalization.normalizer import Normalizer
from app.normalization.openai_client_adapter import OpenAIClientAdapter


class NormalizerFactory:
    """Creates the configured normalizer adapter."""

    OPENAI_COMPATIBLE_BASE_URLS: ClassVar[dict[str, str]] = {
        "openrouter": "https://openrouter.ai/api/v1",
        "groq": "https://api.groq.com/openai/v1",
        "together": "https://api.together.xyz/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "ollama": "http://localhost:11434/v1",
    }

    @classmethod
    def create(cls, settings: Settings) -> BaseNormalizer:
        """Create a configured normalizer from application settings."""
        provider = settings.normalization_provider.lower()
        if provider == "example":
            return Normalizer(
                client=ExampleClientAdapter(),
                model="example",
                temperature=0.0,
            )
        client = OpenAIClientAdapter(
            api_key=cls._resolve_api_key(provider, settings),
            timeout_seconds=cls._resolve_timeout_seconds(provider, settings),
            base_url=cls._resolve_base_url(provider, settings),
        )
        return Normalizer(
            client=client,
            model=cls._resolve_model_name(provider, settings),
            temperature=cls._resolve_temperature(provider, settings),
        )

    @classmethod
    def _resolve_base_url(cls, provider: str, settings: Settings) -> str | None:
        if provider == "openai":
            return None
        if provider == "openai_compatible":
            url = (settings.normalization_openai_compatible_base_url or "").strip()
            if not url:
                raise ValueError(
                    "normalization_openai_compatible_base_url is required for "
                    "normalization_provider=openai_compatible"
                )
            return url
        default_base_url = cls.OPENAI_COMPATIBLE_BASE_URLS.get(provider)
        if default_base_url is not None:
            return default_base_url
        supported = [
            "example",
            "openai",
            "openai_compatible",
            *sorted(cls.OPENAI_COMPATIBLE_BASE_URLS),
        ]
        raise ValueError(
            f"Unknown normalization provider '{provider}'. Choose from: {supported}"
        )

    @classmethod
    def _resolve_api_key(cls, provider: str, settings: Settings) -> str:
        key_map = {
            "openai": settings.normalization_openai_api_key,
            "openai_compatible": settings.normalization_openai_compatible_api_key,
            "openrouter": settings.normalization_openrouter_api_key,
            "groq": settings.normalization_groq_api_key,
            "together": settings.normalization_together_api_key,
            "deepseek": settings.normalization_deepseek_api_key,
            "ollama": settings.normalization_ollama_api_key,
        }
        key = key_map.get(provider, "")
        if not key and provider in cls.OPENAI_COMPATIBLE_BASE_URLS:
            return key
        return key or ""

    @classmethod
    def _resolve_model_name(cls, provider: str, settings: Settings) -> str:
        key_map = {
            "openai": settings.normalization_openai_model_name,
            "openai_compatible": settings.normalization_openai_compatible_model_name,
            "openrouter": settings.normalization_openrouter_model_name,
            "groq": settings.normalization_groq_model_name,
            "together": settings.normalization_together_model_name,
            "deepseek": settings.normalization_deepseek_model_name,
            "ollama": settings.normalization_ollama_model_name,
        }
        return key_map.get(provider, "") or ""

    @classmethod
    def _resolve_timeout_seconds(cls, provider: str, settings: Settings) -> int:
        key_map = {
            "openai": settings.normalization_openai_timeout_seconds,
            "openai_compatible": settings.normalization_openai_compatible_timeout_seconds,
            "openrouter": settings.normalization_openrouter_timeout_seconds,
            "groq": settings.normalization_groq_timeout_seconds,
            "together": settings.normalization_together_timeout_seconds,
            "deepseek": settings.normalization_deepseek_timeout_seconds,
            "ollama": settings.normalization_ollama_timeout_seconds,
        }
        return key_map.get(provider, 30) or 30

    @classmethod
    def _resolve_temperature(cls, provider: str, settings: Settings) -> float:
        if provider == "openai":
            return settings.normalization_openai_temperature
        return 0.0
