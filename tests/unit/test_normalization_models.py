"""Tests for normalization domain models."""

from app.normalization.models import (
    BooleanValue,
    Marker,
    NormalizationResult,
    NumericValue,
    Person,
    ReferenceRange,
    TextValue,
)


class TestPerson:
    def test_frozen(self) -> None:
        p = Person(name="PERSON_1", dob="1990-01-01")
        assert p.name == "PERSON_1"
        assert p.dob == "1990-01-01"

    def test_null_dob(self) -> None:
        p = Person(name="PERSON_1")
        assert p.dob is None


class TestMarkerValues:
    def test_numeric_value(self) -> None:
        v = NumericValue(number=6.2, unit="%")
        assert v.type == "numeric"
        assert v.number == 6.2
        assert v.unit == "%"

    def test_boolean_value(self) -> None:
        v = BooleanValue(value=True)
        assert v.type == "boolean"
        assert v.value is True

    def test_text_value(self) -> None:
        v = TextValue(text="Positive")
        assert v.type == "text"
        assert v.text == "Positive"


class TestMarker:
    def test_marker_with_reference_range(self) -> None:
        m = Marker(
            code="HBA1C",
            name="Hemoglobin A1c",
            value=NumericValue(number=6.2, unit="%"),
            reference_range=ReferenceRange(min=4.0, max=5.6, unit="%"),
        )
        assert m.code == "HBA1C"
        assert m.reference_range is not None
        assert m.reference_range.min == 4.0

    def test_marker_without_reference_range(self) -> None:
        m = Marker(
            code="GLU",
            name="Glucose",
            value=NumericValue(number=5.1, unit="mmol/L"),
        )
        assert m.reference_range is None


class TestNormalizationResult:
    def test_default_markers_empty(self) -> None:
        result = NormalizationResult(person=Person(name="PERSON_1"))
        assert result.markers == []
        assert result.diagnostic_date is None
