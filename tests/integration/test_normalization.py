"""Integration tests for the normalization pipeline.

Uses a mock AI client to test the full pipeline without real API calls.
"""

import json
from unittest.mock import MagicMock

import pytest

from app.normalization.exceptions import (
    NormalizationError,
    NormalizationNetworkError,
    NormalizationValidationError,
)
from app.normalization.models import (
    BooleanValue,
    NumericValue,
    TextValue,
)
from app.normalization.normalizer import Normalizer


def _make_normalizer(response_content: str) -> Normalizer:
    """Create a Normalizer with a mocked AI client returning fixed content."""
    client = MagicMock()
    client.create_chat_completion.return_value = response_content
    return Normalizer(client=client, model="test-model")


def _full_response(markers: list[dict[str, object]] | None = None) -> str:
    return json.dumps({
        "person": {"name": "PERSON_1", "dob": "1985-03-15"},
        "diagnostic_date": "2025-01-10",
        "markers": markers or [],
    })


class TestFullNormalizationPipeline:
    def test_end_to_end_with_multiple_marker_types(self) -> None:
        markers: list[dict[str, object]] = [
            {
                "code": "HBA1C",
                "name": "Hemoglobin A1c",
                "value": {"type": "numeric", "number": 6.2, "unit": "%"},
                "reference_range": {"min": 4.0, "max": 5.6, "unit": "%"},
            },
            {
                "code": "HIV",
                "name": "HIV Antibody Test",
                "value": {"type": "boolean", "value": False},
            },
            {
                "code": "BLOOD_TYPE",
                "name": "Blood Type",
                "value": {"type": "text", "text": "A+"},
            },
        ]
        normalizer = _make_normalizer(_full_response(markers))
        result = normalizer.normalize("Patient PERSON_1\nHbA1c 6.2%")

        assert result.person.name == "PERSON_1"
        assert result.person.dob == "1985-03-15"
        assert result.diagnostic_date == "2025-01-10"
        assert len(result.markers) == 3
        assert isinstance(result.markers[0].value, NumericValue)
        assert isinstance(result.markers[1].value, BooleanValue)
        assert isinstance(result.markers[2].value, TextValue)

    def test_empty_markers_is_valid(self) -> None:
        normalizer = _make_normalizer(_full_response())
        result = normalizer.normalize("Patient PERSON_1")
        assert result.markers == []

    def test_null_dates(self) -> None:
        content = json.dumps({
            "person": {"name": "PERSON_1", "dob": None},
            "diagnostic_date": None,
            "markers": [],
        })
        normalizer = _make_normalizer(content)
        result = normalizer.normalize("text")
        assert result.person.dob is None
        assert result.diagnostic_date is None


class TestFullPipelineValidationFailures:
    def test_over_100_markers_fails(self) -> None:
        markers: list[dict[str, object]] = [
            {
                "code": f"M{i}",
                "name": f"Marker {i}",
                "value": {"type": "numeric", "number": float(i), "unit": "u"},
            }
            for i in range(101)
        ]
        normalizer = _make_normalizer(_full_response(markers))
        with pytest.raises(NormalizationValidationError, match="Too many markers"):
            normalizer.normalize("text")

    def test_duplicate_marker_codes_fails(self) -> None:
        markers: list[dict[str, object]] = [
            {"code": "GLU", "name": "Glucose",
             "value": {"type": "numeric", "number": 5.1, "unit": "mmol/L"}},
            {"code": "GLU", "name": "Glucose 2",
             "value": {"type": "numeric", "number": 5.8, "unit": "mmol/L"}},
        ]
        normalizer = _make_normalizer(_full_response(markers))
        with pytest.raises(NormalizationValidationError, match="Duplicate"):
            normalizer.normalize("text")

    def test_invalid_json_fails(self) -> None:
        normalizer = _make_normalizer("not valid json {{{")
        with pytest.raises(NormalizationError, match="Invalid JSON"):
            normalizer.normalize("text")

    def test_missing_required_fields_fails(self) -> None:
        normalizer = _make_normalizer(json.dumps({"person": {"name": "PERSON_1"}}))
        with pytest.raises(NormalizationValidationError):
            normalizer.normalize("text")

    def test_invalid_value_type_fails(self) -> None:
        markers: list[dict[str, object]] = [{
            "code": "X",
            "name": "Test",
            "value": {"type": "unknown"},
        }]
        normalizer = _make_normalizer(_full_response(markers))
        with pytest.raises(NormalizationValidationError, match=r"value\.type"):
            normalizer.normalize("text")


class TestNetworkFailureSimulation:
    def test_connection_error_is_network_error(self) -> None:
        client = MagicMock()
        client.create_chat_completion.side_effect = NormalizationNetworkError("connection failed")
        normalizer = Normalizer(client=client, model="test-model")
        with pytest.raises(NormalizationNetworkError):
            normalizer.normalize("text")

    def test_api_error_is_network_error(self) -> None:
        client = MagicMock()
        client.create_chat_completion.side_effect = NormalizationNetworkError("api failed")
        normalizer = Normalizer(client=client, model="test-model")
        with pytest.raises(NormalizationNetworkError):
            normalizer.normalize("text")
