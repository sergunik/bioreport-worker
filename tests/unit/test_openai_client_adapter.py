from unittest.mock import MagicMock, patch

import httpx
import openai
import pytest

from app.normalization.exceptions import NormalizationError, NormalizationNetworkError
from app.normalization.openai_client_adapter import OpenAIClientAdapter


def _make_mock_response(content: str | None) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


class TestOpenAIClientAdapter:
    def test_returns_content(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response('{"ok": true}')
        with patch(
            "app.normalization.openai_client_adapter.openai.OpenAI",
            return_value=mock_client,
        ):
            adapter = OpenAIClientAdapter(
                api_key="k",
                timeout_seconds=30,
                base_url=None,
            )
            content = adapter.create_chat_completion(
                model="m",
                temperature=0.1,
                system_prompt="system",
                user_prompt="user",
                json_schema={"type": "object"},
            )
        assert content == '{"ok": true}'

    def test_raises_error_for_empty_content(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response(None)
        with patch(
            "app.normalization.openai_client_adapter.openai.OpenAI",
            return_value=mock_client,
        ):
            adapter = OpenAIClientAdapter(
                api_key="k",
                timeout_seconds=30,
                base_url=None,
            )
            with pytest.raises(NormalizationError, match="empty response"):
                adapter.create_chat_completion(
                    model="m",
                    temperature=0.1,
                    system_prompt="system",
                    user_prompt="user",
                    json_schema={"type": "object"},
                )

    def test_raises_network_error_on_connection_failure(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APIConnectionError(
            request=MagicMock()
        )
        with patch(
            "app.normalization.openai_client_adapter.openai.OpenAI",
            return_value=mock_client,
        ):
            adapter = OpenAIClientAdapter(
                api_key="k",
                timeout_seconds=30,
                base_url=None,
            )
            with pytest.raises(NormalizationNetworkError, match="network error"):
                adapter.create_chat_completion(
                    model="m",
                    temperature=0.1,
                    system_prompt="system",
                    user_prompt="user",
                    json_schema={"type": "object"},
                )

    def test_raises_network_error_on_timeout(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = httpx.TimeoutException("timeout")
        with patch(
            "app.normalization.openai_client_adapter.openai.OpenAI",
            return_value=mock_client,
        ):
            adapter = OpenAIClientAdapter(
                api_key="k",
                timeout_seconds=30,
                base_url=None,
            )
            with pytest.raises(NormalizationNetworkError, match="network error"):
                adapter.create_chat_completion(
                    model="m",
                    temperature=0.1,
                    system_prompt="system",
                    user_prompt="user",
                    json_schema={"type": "object"},
                )

    def test_raises_network_error_on_api_error(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APIError(
            message="server error",
            request=MagicMock(),
            body=None,
        )
        with patch(
            "app.normalization.openai_client_adapter.openai.OpenAI",
            return_value=mock_client,
        ):
            adapter = OpenAIClientAdapter(
                api_key="k",
                timeout_seconds=30,
                base_url=None,
            )
            with pytest.raises(NormalizationNetworkError, match="API error"):
                adapter.create_chat_completion(
                    model="m",
                    temperature=0.1,
                    system_prompt="system",
                    user_prompt="user",
                    json_schema={"type": "object"},
                )
