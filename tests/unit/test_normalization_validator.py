"""Tests for normalization validator (Step 5.5 domain invariants)."""

import pytest

from app.normalization.exceptions import NormalizationValidationError
from app.normalization.models import (
    BooleanValue,
    NormalizationResult,
    NumericValue,
    Person,
    ReferenceRange,
    TextValue,
)
from app.normalization.validator import validate_and_build


def _valid_data(
    markers: list[dict[str, object]] | None = None,
    pii: list[str] | None = None,
) -> dict[str, object]:
    """Build a minimal valid normalization payload."""
    return {
        "person": {"name": "PERSON_1", "dob": "1990-01-01"},
        "diagnostic_date": "2025-01-10",
        "diagnostic_title": "Blood panel",
        "language": "en",
        "markers": markers or [],
        "pii": pii or [],
    }


def _numeric_marker(
    code: str = "HBA1C",
    name: str = "Hemoglobin A1c",
    number: float = 6.2,
    unit: str = "%",
    ref_range: dict[str, object] | None = None,
) -> dict[str, object]:
    m: dict[str, object] = {
        "code": code,
        "name": name,
        "value": {"type": "numeric", "number": number, "unit": unit},
    }
    if ref_range is not None:
        m["reference_range"] = ref_range
    return m


class TestValidPayloads:
    def test_empty_markers(self) -> None:
        result = validate_and_build(_valid_data())
        assert isinstance(result, NormalizationResult)
        assert result.markers == []

    def test_single_numeric_marker(self) -> None:
        data = _valid_data(markers=[_numeric_marker()])
        result = validate_and_build(data)
        assert len(result.markers) == 1
        marker = result.markers[0]
        assert marker.code == "HBA1C"
        assert marker.name == "Hemoglobin A1c"
        assert isinstance(marker.value, NumericValue)
        assert marker.value.number == 6.2
        assert marker.value.unit == "%"

    def test_boolean_marker(self) -> None:
        data = _valid_data(markers=[{
            "code": "HIV",
            "name": "HIV Test",
            "value": {"type": "boolean", "value": True},
        }])
        result = validate_and_build(data)
        assert isinstance(result.markers[0].value, BooleanValue)
        assert result.markers[0].value.value is True

    def test_text_marker(self) -> None:
        data = _valid_data(markers=[{
            "code": "BLOOD_TYPE",
            "name": "Blood Type",
            "value": {"type": "text", "text": "A+"},
        }])
        result = validate_and_build(data)
        assert isinstance(result.markers[0].value, TextValue)
        assert result.markers[0].value.text == "A+"

    def test_marker_with_reference_range(self) -> None:
        data = _valid_data(markers=[
            _numeric_marker(ref_range={"min": 4.0, "max": 5.6, "unit": "%"})
        ])
        result = validate_and_build(data)
        ref = result.markers[0].reference_range
        assert ref is not None
        assert isinstance(ref, ReferenceRange)
        assert ref.min == 4.0
        assert ref.max == 5.6
        assert ref.unit == "%"

    def test_marker_with_null_reference_range(self) -> None:
        data = _valid_data(markers=[_numeric_marker()])
        data_markers = data["markers"]
        assert isinstance(data_markers, list)
        data_markers[0]["reference_range"] = None  # type: ignore[index]
        result = validate_and_build(data)
        assert result.markers[0].reference_range is None

    def test_null_diagnostic_date(self) -> None:
        data = _valid_data()
        data["diagnostic_date"] = None
        result = validate_and_build(data)
        assert result.diagnostic_date is None

    def test_null_dob(self) -> None:
        data = _valid_data()
        assert isinstance(data["person"], dict)
        data["person"]["dob"] = None  # type: ignore[index]
        result = validate_and_build(data)
        assert result.person.dob is None

    def test_person_fields(self) -> None:
        result = validate_and_build(_valid_data())
        assert isinstance(result.person, Person)
        assert result.person.name == "PERSON_1"
        assert result.person.dob == "1990-01-01"
        assert result.diagnostic_title == "Blood panel"

    def test_multiple_markers_different_types(self) -> None:
        data = _valid_data(markers=[
            _numeric_marker(code="GLU", name="Glucose", number=5.1, unit="mmol/L"),
            {"code": "HIV", "name": "HIV Test", "value": {"type": "boolean", "value": False}},
            {"code": "BLOOD_TYPE", "name": "Blood Type", "value": {"type": "text", "text": "O-"}},
        ])
        result = validate_and_build(data)
        assert len(result.markers) == 3

    def test_reference_range_with_null_min(self) -> None:
        data = _valid_data(markers=[
            _numeric_marker(ref_range={"min": None, "max": 5.6, "unit": "%"})
        ])
        result = validate_and_build(data)
        ref = result.markers[0].reference_range
        assert ref is not None
        assert ref.min is None
        assert ref.max == 5.6

    def test_integer_number_converted_to_float(self) -> None:
        data = _valid_data(markers=[_numeric_marker(number=6)])
        result = validate_and_build(data)
        assert isinstance(result.markers[0].value, NumericValue)
        assert result.markers[0].value.number == 6.0


class TestMissingTopLevelFields:
    def test_missing_person(self) -> None:
        data = _valid_data()
        del data["person"]
        with pytest.raises(NormalizationValidationError, match="person"):
            validate_and_build(data)

    def test_missing_diagnostic_date(self) -> None:
        data = _valid_data()
        del data["diagnostic_date"]
        with pytest.raises(NormalizationValidationError, match="diagnostic_date"):
            validate_and_build(data)

    def test_missing_markers(self) -> None:
        data = _valid_data()
        del data["markers"]
        with pytest.raises(NormalizationValidationError, match="markers"):
            validate_and_build(data)

    def test_missing_diagnostic_title(self) -> None:
        data = _valid_data()
        del data["diagnostic_title"]
        with pytest.raises(NormalizationValidationError, match="diagnostic_title"):
            validate_and_build(data)


class TestPersonValidation:
    def test_person_not_dict(self) -> None:
        data = _valid_data()
        data["person"] = "not a dict"
        with pytest.raises(NormalizationValidationError, match=r"person.*object"):
            validate_and_build(data)

    def test_person_missing_name(self) -> None:
        data = _valid_data()
        data["person"] = {"dob": "1990-01-01"}
        with pytest.raises(NormalizationValidationError, match=r"person\.name"):
            validate_and_build(data)

    def test_person_empty_name(self) -> None:
        data = _valid_data()
        data["person"] = {"name": ""}
        with pytest.raises(NormalizationValidationError, match=r"person\.name"):
            validate_and_build(data)

    def test_person_dob_wrong_type(self) -> None:
        data = _valid_data()
        data["person"] = {"name": "PERSON_1", "dob": 123}
        with pytest.raises(NormalizationValidationError, match=r"person\.dob"):
            validate_and_build(data)


class TestDiagnosticTitleValidation:
    def test_diagnostic_title_passed_through(self) -> None:
        data = _valid_data()
        data["diagnostic_title"] = "CBC"
        result = validate_and_build(data)
        assert result.diagnostic_title == "CBC"

    def test_diagnostic_title_wrong_type(self) -> None:
        data = _valid_data()
        data["diagnostic_title"] = 123
        with pytest.raises(NormalizationValidationError, match="diagnostic_title"):
            validate_and_build(data)

    def test_diagnostic_title_null_invalid(self) -> None:
        data = _valid_data()
        data["diagnostic_title"] = None
        with pytest.raises(NormalizationValidationError, match="diagnostic_title"):
            validate_and_build(data)

    def test_diagnostic_title_over_50_chars(self) -> None:
        data = _valid_data()
        data["diagnostic_title"] = "x" * 51
        with pytest.raises(NormalizationValidationError, match="50"):
            validate_and_build(data)

    def test_diagnostic_title_exactly_50_ok(self) -> None:
        data = _valid_data()
        data["diagnostic_title"] = "x" * 50
        result = validate_and_build(data)
        assert result.diagnostic_title == "x" * 50


class TestMarkersValidation:
    def test_markers_not_list(self) -> None:
        data = _valid_data()
        data["markers"] = "not a list"
        with pytest.raises(NormalizationValidationError, match=r"markers.*list"):
            validate_and_build(data)

    def test_too_many_markers(self) -> None:
        markers = [
            _numeric_marker(code=f"M{i}", name=f"Marker {i}")
            for i in range(101)
        ]
        data = _valid_data(markers=markers)
        with pytest.raises(NormalizationValidationError, match="Too many markers"):
            validate_and_build(data)

    def test_exactly_100_markers_ok(self) -> None:
        markers = [
            _numeric_marker(code=f"M{i}", name=f"Marker {i}")
            for i in range(100)
        ]
        result = validate_and_build(_valid_data(markers=markers))
        assert len(result.markers) == 100

    def test_duplicate_marker_codes(self) -> None:
        data = _valid_data(markers=[
            _numeric_marker(code="HBA1C"),
            _numeric_marker(code="HBA1C", name="Other"),
        ])
        with pytest.raises(NormalizationValidationError, match="Duplicate marker code"):
            validate_and_build(data)

    def test_duplicate_codes_case_insensitive(self) -> None:
        data = _valid_data(markers=[
            _numeric_marker(code="hba1c"),
            _numeric_marker(code="HBA1C", name="Other"),
        ])
        with pytest.raises(NormalizationValidationError, match="Duplicate marker code"):
            validate_and_build(data)

    def test_marker_not_object(self) -> None:
        data = _valid_data(markers=["not a dict"])
        with pytest.raises(NormalizationValidationError, match=r"index 0.*object"):
            validate_and_build(data)

    def test_marker_missing_code(self) -> None:
        data = _valid_data(markers=[{"name": "Test", "value": {"type": "text", "text": "x"}}])
        with pytest.raises(NormalizationValidationError, match=r"code.*non-empty"):
            validate_and_build(data)

    def test_marker_empty_code(self) -> None:
        data = _valid_data(markers=[
            {"code": "", "name": "Test", "value": {"type": "text", "text": "x"}},
        ])
        with pytest.raises(NormalizationValidationError, match=r"code.*non-empty"):
            validate_and_build(data)

    def test_marker_missing_name(self) -> None:
        data = _valid_data(markers=[{"code": "X", "value": {"type": "text", "text": "x"}}])
        with pytest.raises(NormalizationValidationError, match=r"name.*non-empty"):
            validate_and_build(data)

    def test_marker_missing_value(self) -> None:
        data = _valid_data(markers=[{"code": "X", "name": "Test"}])
        with pytest.raises(NormalizationValidationError, match=r"value.*object"):
            validate_and_build(data)


class TestValueTypeValidation:
    def test_invalid_value_type(self) -> None:
        data = _valid_data(markers=[{
            "code": "X", "name": "Test",
            "value": {"type": "invalid"},
        }])
        with pytest.raises(NormalizationValidationError, match=r"value\.type"):
            validate_and_build(data)

    def test_numeric_value_missing_number(self) -> None:
        data = _valid_data(markers=[{
            "code": "X", "name": "Test",
            "value": {"type": "numeric", "unit": "%"},
        }])
        with pytest.raises(NormalizationValidationError, match=r"value\.number"):
            validate_and_build(data)

    def test_numeric_value_string_number(self) -> None:
        data = _valid_data(markers=[{
            "code": "X", "name": "Test",
            "value": {"type": "numeric", "number": "6.2", "unit": "%"},
        }])
        with pytest.raises(NormalizationValidationError, match=r"value\.number"):
            validate_and_build(data)

    def test_boolean_value_missing(self) -> None:
        data = _valid_data(markers=[{
            "code": "X", "name": "Test",
            "value": {"type": "boolean"},
        }])
        with pytest.raises(NormalizationValidationError, match=r"value\.value.*boolean"):
            validate_and_build(data)

    def test_boolean_value_wrong_type(self) -> None:
        data = _valid_data(markers=[{
            "code": "X", "name": "Test",
            "value": {"type": "boolean", "value": "true"},
        }])
        with pytest.raises(NormalizationValidationError, match=r"value\.value.*boolean"):
            validate_and_build(data)

    def test_text_value_missing(self) -> None:
        data = _valid_data(markers=[{
            "code": "X", "name": "Test",
            "value": {"type": "text"},
        }])
        with pytest.raises(NormalizationValidationError, match=r"value\.text"):
            validate_and_build(data)

    def test_text_value_wrong_type(self) -> None:
        data = _valid_data(markers=[{
            "code": "X", "name": "Test",
            "value": {"type": "text", "text": 42},
        }])
        with pytest.raises(NormalizationValidationError, match=r"value\.text"):
            validate_and_build(data)

    def test_value_not_object(self) -> None:
        data = _valid_data(markers=[{
            "code": "X", "name": "Test",
            "value": "not an object",
        }])
        with pytest.raises(NormalizationValidationError, match=r"value.*object"):
            validate_and_build(data)


class TestReferenceRangeValidation:
    def test_reference_range_not_object(self) -> None:
        marker = _numeric_marker()
        marker["reference_range"] = "not an object"
        data = _valid_data(markers=[marker])
        with pytest.raises(NormalizationValidationError, match=r"reference_range.*object"):
            validate_and_build(data)

    def test_reference_range_min_wrong_type(self) -> None:
        marker = _numeric_marker()
        marker["reference_range"] = {"min": "low", "max": 5.6, "unit": "%"}
        data = _valid_data(markers=[marker])
        with pytest.raises(NormalizationValidationError, match=r"reference_range\.min"):
            validate_and_build(data)

    def test_reference_range_max_wrong_type(self) -> None:
        marker = _numeric_marker()
        marker["reference_range"] = {"min": 4.0, "max": "high", "unit": "%"}
        data = _valid_data(markers=[marker])
        with pytest.raises(NormalizationValidationError, match=r"reference_range\.max"):
            validate_and_build(data)

    def test_reference_range_unit_wrong_type(self) -> None:
        marker = _numeric_marker()
        marker["reference_range"] = {"min": 4.0, "max": 5.6, "unit": 123}
        data = _valid_data(markers=[marker])
        with pytest.raises(NormalizationValidationError, match=r"reference_range\.unit"):
            validate_and_build(data)


class TestDiagnosticDateValidation:
    def test_diagnostic_date_wrong_type(self) -> None:
        data = _valid_data()
        data["diagnostic_date"] = 12345
        with pytest.raises(NormalizationValidationError, match="diagnostic_date"):
            validate_and_build(data)


class TestLanguageValidation:
    def test_language_string(self) -> None:
        data = _valid_data()
        data["language"] = "uk"
        result = validate_and_build(data)
        assert result.language == "uk"

    def test_language_null(self) -> None:
        data = _valid_data()
        data["language"] = None
        result = validate_and_build(data)
        assert result.language is None

    def test_language_missing_raises(self) -> None:
        data = _valid_data()
        del data["language"]
        with pytest.raises(NormalizationValidationError, match=r"Missing required.*language"):
            validate_and_build(data)

    def test_language_wrong_type(self) -> None:
        data = _valid_data()
        data["language"] = 42
        with pytest.raises(NormalizationValidationError, match="language"):
            validate_and_build(data)


class TestPiiValidation:
    def test_pii_empty_list(self) -> None:
        data = _valid_data(pii=[])
        result = validate_and_build(data)
        assert result.pii == []

    def test_pii_with_values(self) -> None:
        data = _valid_data(pii=["Jan Kowalski", "1990-01-01"])
        result = validate_and_build(data)
        assert result.pii == ["Jan Kowalski", "1990-01-01"]

    def test_pii_missing_raises(self) -> None:
        data = _valid_data()
        del data["pii"]
        with pytest.raises(NormalizationValidationError, match=r"Missing required.*pii"):
            validate_and_build(data)

    def test_pii_null_defaults_to_empty(self) -> None:
        data = _valid_data()
        data["pii"] = None
        result = validate_and_build(data)
        assert result.pii == []

    def test_pii_not_list(self) -> None:
        data = _valid_data()
        data["pii"] = "not a list"
        with pytest.raises(NormalizationValidationError, match=r"pii.*list"):
            validate_and_build(data)

    def test_pii_item_not_string(self) -> None:
        data = _valid_data()
        data["pii"] = ["valid", 42]
        with pytest.raises(NormalizationValidationError, match=r"pii\[1\].*string"):
            validate_and_build(data)
