"""Tests for NormalizerFactory."""

from unittest.mock import patch

import pytest

from app.config.settings import Settings
from app.normalization.base import BaseNormalizer
from app.normalization.factory import NormalizerFactory
from app.normalization.normalizer import Normalizer


class TestNormalizerFactory:
    def test_creates_example_adapter_for_example_provider(self) -> None:
        settings = Settings(normalization_provider="example")
        normalizer = NormalizerFactory.create(settings)
        assert isinstance(normalizer, BaseNormalizer)
        assert isinstance(normalizer, Normalizer)
        result = normalizer.normalize("any text")
        assert result.person.name == "PERSON_1"
        assert result.markers == []

    def test_creates_normalizer(self) -> None:
        settings = Settings(
            normalization_provider="openai",
            normalization_openai_api_key="test-key",
            normalization_openai_model_name="gpt-4",
        )
        with patch("app.normalization.factory.OpenAIClientAdapter"):
            normalizer = NormalizerFactory.create(settings)
        assert isinstance(normalizer, BaseNormalizer)
        assert isinstance(normalizer, Normalizer)

    def test_uses_openai_settings(self) -> None:
        settings = Settings(
            normalization_provider="openai",
            normalization_openai_api_key="openai-key",
            normalization_openai_model_name="gpt-4",
            normalization_openai_timeout_seconds=42,
        )
        with patch("app.normalization.factory.OpenAIClientAdapter") as mock_adapter:
            NormalizerFactory.create(settings)
        mock_adapter.assert_called_once_with(
            api_key="openai-key",
            timeout_seconds=42,
            base_url=None,
        )

    def test_uses_provider_default_base_url_for_openrouter(self) -> None:
        settings = Settings(
            normalization_provider="openrouter",
            normalization_openrouter_api_key="k",
            normalization_openrouter_model_name="m",
        )
        with patch("app.normalization.factory.OpenAIClientAdapter") as mock_adapter:
            NormalizerFactory.create(settings)
        mock_adapter.assert_called_once_with(
            api_key="k",
            timeout_seconds=30,
            base_url="https://openrouter.ai/api/v1",
        )

    def test_uses_custom_base_url_for_openai_compatible(self) -> None:
        settings = Settings(
            normalization_provider="openai_compatible",
            normalization_openai_compatible_api_key="k",
            normalization_openai_compatible_model_name="m",
            normalization_openai_compatible_base_url="https://example.com/v1",
        )
        with patch("app.normalization.factory.OpenAIClientAdapter") as mock_adapter:
            NormalizerFactory.create(settings)
        mock_adapter.assert_called_once_with(
            api_key="k",
            timeout_seconds=30,
            base_url="https://example.com/v1",
        )

    def test_openai_compatible_requires_base_url(self) -> None:
        settings = Settings(
            normalization_provider="openai_compatible",
            normalization_openai_compatible_api_key="k",
            normalization_openai_compatible_model_name="m",
        )
        with pytest.raises(ValueError, match="normalization_openai_compatible_base_url"):
            NormalizerFactory.create(settings)

    def test_unknown_provider_raises_value_error(self) -> None:
        settings = Settings(
            normalization_provider="unknown",
            normalization_openai_api_key="k",
            normalization_openai_model_name="m",
        )
        with pytest.raises(ValueError, match="Unknown normalization provider"):
            NormalizerFactory.create(settings)
