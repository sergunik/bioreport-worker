"""Tests for the Normalizer (AI-powered normalization)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.normalization.exceptions import (
    NormalizationError,
    NormalizationNetworkError,
    NormalizationValidationError,
)
from app.normalization.normalizer import Normalizer


def _make_normalizer(client: MagicMock | None = None) -> Normalizer:
    if client is None:
        client = MagicMock()
    return Normalizer(client=client, model="test-model")


def _mock_ai_response(client: MagicMock, content: str) -> None:
    """Configure the mock client to return the given content."""
    client.create_chat_completion.return_value = content


def _valid_json_response(
    markers: list[dict[str, object]] | None = None,
) -> str:
    return json.dumps({
        "person": {"name": "PERSON_1", "dob": "1990-01-01"},
        "diagnostic_date": "2025-01-10",
        "markers": markers or [],
    })


class TestNormalizeSuccess:
    def test_returns_normalization_result(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, _valid_json_response())
        normalizer = _make_normalizer(client)
        result = normalizer.normalize("some text")
        assert result.person.name == "PERSON_1"
        assert result.diagnostic_date == "2025-01-10"
        assert result.markers == []

    def test_extracts_markers(self) -> None:
        client = MagicMock()
        markers = [{
            "code": "HBA1C",
            "name": "Hemoglobin A1c",
            "value": {"type": "numeric", "number": 6.2, "unit": "%"},
            "reference_range": {"min": 4.0, "max": 5.6, "unit": "%"},
        }]
        _mock_ai_response(client, _valid_json_response(markers))
        normalizer = _make_normalizer(client)
        result = normalizer.normalize("some text")
        assert len(result.markers) == 1
        assert result.markers[0].code == "HBA1C"

    def test_passes_input_text_to_prompt(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, _valid_json_response())
        normalizer = _make_normalizer(client)
        normalizer.normalize("clinical input")
        call_args = client.create_chat_completion.call_args
        user_msg = call_args.kwargs["user_prompt"]
        assert "clinical input" in user_msg

    def test_calls_ai_with_model(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, _valid_json_response())
        normalizer = _make_normalizer(client)
        normalizer.normalize("text")
        call_args = client.create_chat_completion.call_args
        assert call_args.kwargs["model"] == "test-model"

    def test_calls_ai_with_temperature_in_valid_range(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, _valid_json_response())
        normalizer = Normalizer(client=client, model="m", temperature=0.1)
        normalizer.normalize("text")
        call_args = client.create_chat_completion.call_args
        assert call_args.kwargs["temperature"] == 0.1

    def test_clamps_temperature_to_zero_to_point_two(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, _valid_json_response())
        normalizer = Normalizer(client=client, model="m", temperature=0.5)
        normalizer.normalize("text")
        call_args = client.create_chat_completion.call_args
        assert call_args.kwargs["temperature"] == 0.2

    def test_passes_json_schema(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, _valid_json_response())
        normalizer = _make_normalizer(client)
        normalizer.normalize("text")
        call_args = client.create_chat_completion.call_args
        schema = call_args.kwargs["json_schema"]
        assert schema.get("properties", {}).get("person") is not None


class TestJsonParsing:
    def test_strips_markdown_code_fences(self) -> None:
        client = MagicMock()
        content = "```json\n" + _valid_json_response() + "\n```"
        _mock_ai_response(client, content)
        normalizer = _make_normalizer(client)
        result = normalizer.normalize("text")
        assert result.person.name == "PERSON_1"

    def test_strips_plain_code_fences(self) -> None:
        client = MagicMock()
        content = "```\n" + _valid_json_response() + "\n```"
        _mock_ai_response(client, content)
        normalizer = _make_normalizer(client)
        result = normalizer.normalize("text")
        assert result.person.name == "PERSON_1"

    def test_invalid_json_raises_error(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, "not valid json")
        normalizer = _make_normalizer(client)
        with pytest.raises(NormalizationError, match="Invalid JSON"):
            normalizer.normalize("text")

    def test_json_array_raises_error(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, "[]")
        normalizer = _make_normalizer(client)
        with pytest.raises(NormalizationError, match="must be an object"):
            normalizer.normalize("text")

    def test_empty_ai_response_raises_error(self) -> None:
        client = MagicMock()
        client.create_chat_completion.side_effect = NormalizationError("AI returned empty response")
        normalizer = _make_normalizer(client)
        with pytest.raises(NormalizationError, match="empty response"):
            normalizer.normalize("text")


class TestNetworkErrors:
    def test_connection_error_raises_network_error(self) -> None:
        client = MagicMock()
        client.create_chat_completion.side_effect = NormalizationNetworkError("network")
        normalizer = _make_normalizer(client)
        with pytest.raises(NormalizationNetworkError, match="network"):
            normalizer.normalize("text")

    def test_timeout_raises_network_error(self) -> None:
        client = MagicMock()
        client.create_chat_completion.side_effect = NormalizationNetworkError("network timeout")
        normalizer = _make_normalizer(client)
        with pytest.raises(NormalizationNetworkError, match="network timeout"):
            normalizer.normalize("text")

    def test_api_error_raises_network_error(self) -> None:
        client = MagicMock()
        client.create_chat_completion.side_effect = NormalizationNetworkError("API error")
        normalizer = _make_normalizer(client)
        with pytest.raises(NormalizationNetworkError, match="API error"):
            normalizer.normalize("text")


class TestValidationFailures:
    def test_missing_person_raises_validation_error(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, json.dumps({
            "diagnostic_date": "2025-01-10",
            "markers": [],
        }))
        normalizer = _make_normalizer(client)
        with pytest.raises(NormalizationValidationError, match="person"):
            normalizer.normalize("text")

    def test_duplicate_markers_raises_validation_error(self) -> None:
        client = MagicMock()
        markers: list[dict[str, object]] = [
            {"code": "GLU", "name": "Glucose",
             "value": {"type": "numeric", "number": 5.1, "unit": "mmol/L"}},
            {"code": "GLU", "name": "Glucose 2",
             "value": {"type": "numeric", "number": 5.8, "unit": "mmol/L"}},
        ]
        _mock_ai_response(client, _valid_json_response(markers))
        normalizer = _make_normalizer(client)
        with pytest.raises(NormalizationValidationError, match="Duplicate"):
            normalizer.normalize("text")


class TestDebugLogging:
    def test_logs_prompt_in_debug(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, _valid_json_response())
        normalizer = _make_normalizer(client)
        with patch("app.normalization.normalizer.Log") as mock_log:
            normalizer.normalize("test text")
            debug_calls = [c for c in mock_log.debug.call_args_list]
            assert len(debug_calls) >= 1
            # First debug call should contain the prompt
            assert "prompt" in debug_calls[0].args[0].lower()

    def test_logs_marker_count_in_info(self) -> None:
        client = MagicMock()
        _mock_ai_response(client, _valid_json_response())
        normalizer = _make_normalizer(client)
        with patch("app.normalization.normalizer.Log") as mock_log:
            normalizer.normalize("test text")
            info_calls = [c for c in mock_log.info.call_args_list]
            assert any("0 markers" in c.args[0] for c in info_calls)
