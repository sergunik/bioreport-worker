"""Validates raw parsed JSON against domain invariants (Step 5.5)."""

from typing import Any

from app.normalization.exceptions import NormalizationValidationError
from app.normalization.models import (
    BooleanValue,
    Marker,
    MarkerValue,
    NormalizationResult,
    NumericValue,
    Person,
    ReferenceRange,
    TextValue,
)

_MAX_MARKERS = 100
_VALID_VALUE_TYPES = frozenset({"numeric", "boolean", "text"})


def validate_and_build(data: dict[str, Any]) -> NormalizationResult:
    """Validate raw parsed JSON and build a NormalizationResult.

    Enforces all domain invariants from the spec.

    Raises:
        NormalizationValidationError: on any validation failure.
    """
    _require_top_level_fields(data)
    person = _build_person(data["person"])
    diagnostic_date = _build_diagnostic_date(data.get("diagnostic_date"))
    markers = _build_markers(data["markers"])
    return NormalizationResult(person=person, diagnostic_date=diagnostic_date, markers=markers)


def _require_top_level_fields(data: dict[str, Any]) -> None:
    for field in ("person", "diagnostic_date", "markers"):
        if field not in data:
            raise NormalizationValidationError(f"Missing required top-level field: {field}")


def _build_person(raw: Any) -> Person:
    if not isinstance(raw, dict):
        raise NormalizationValidationError("'person' must be an object")
    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise NormalizationValidationError("'person.name' must be a non-empty string")
    dob = raw.get("dob")
    if dob is not None and not isinstance(dob, str):
        raise NormalizationValidationError("'person.dob' must be a string or null")
    return Person(name=name, dob=dob)


def _build_diagnostic_date(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise NormalizationValidationError("'diagnostic_date' must be a string or null")
    return raw


def _build_markers(raw: Any) -> list[Marker]:
    if not isinstance(raw, list):
        raise NormalizationValidationError("'markers' must be a list")
    if len(raw) > _MAX_MARKERS:
        raise NormalizationValidationError(
            f"Too many markers: {len(raw)} (max {_MAX_MARKERS})"
        )
    seen_codes: set[str] = set()
    markers: list[Marker] = []
    for i, item in enumerate(raw):
        marker = _build_marker(item, i)
        code_upper = marker.code.upper()
        if code_upper in seen_codes:
            raise NormalizationValidationError(f"Duplicate marker code: {marker.code}")
        seen_codes.add(code_upper)
        markers.append(marker)
    return markers


def _build_marker(raw: Any, index: int) -> Marker:
    if not isinstance(raw, dict):
        raise NormalizationValidationError(f"Marker at index {index} must be an object")
    code = raw.get("code")
    if not code or not isinstance(code, str):
        raise NormalizationValidationError(
            f"Marker at index {index}: 'code' must be a non-empty string"
        )
    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise NormalizationValidationError(
            f"Marker at index {index}: 'name' must be a non-empty string"
        )
    value = _build_value(raw.get("value"), index)
    ref_range = _build_reference_range(raw.get("reference_range"), index)
    return Marker(code=code, name=name, value=value, reference_range=ref_range)


def _build_value(raw: Any, marker_index: int) -> MarkerValue:
    if not isinstance(raw, dict):
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'value' must be an object"
        )
    vtype = raw.get("type")
    if vtype not in _VALID_VALUE_TYPES:
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'value.type' must be one of "
            f"{sorted(_VALID_VALUE_TYPES)}, got {vtype!r}"
        )
    if vtype == "numeric":
        return _build_numeric_value(raw, marker_index)
    if vtype == "boolean":
        return _build_boolean_value(raw, marker_index)
    return _build_text_value(raw, marker_index)


def _build_numeric_value(raw: dict[str, Any], marker_index: int) -> NumericValue:
    number = raw.get("number")
    if not isinstance(number, (int, float)):
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'value.number' must be a number"
        )
    unit = raw.get("unit", "")
    if not isinstance(unit, str):
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'value.unit' must be a string"
        )
    return NumericValue(number=float(number), unit=unit)


def _build_boolean_value(raw: dict[str, Any], marker_index: int) -> BooleanValue:
    val = raw.get("value")
    if not isinstance(val, bool):
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'value.value' must be a boolean"
        )
    return BooleanValue(value=val)


def _build_text_value(raw: dict[str, Any], marker_index: int) -> TextValue:
    text = raw.get("text")
    if not isinstance(text, str):
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'value.text' must be a string"
        )
    return TextValue(text=text)


def _build_reference_range(raw: Any, marker_index: int) -> ReferenceRange | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'reference_range' must be an object or null"
        )
    min_val = raw.get("min")
    max_val = raw.get("max")
    unit = raw.get("unit", "")
    if min_val is not None and not isinstance(min_val, (int, float)):
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'reference_range.min' must be a number or null"
        )
    if max_val is not None and not isinstance(max_val, (int, float)):
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'reference_range.max' must be a number or null"
        )
    if not isinstance(unit, str):
        raise NormalizationValidationError(
            f"Marker at index {marker_index}: 'reference_range.unit' must be a string"
        )
    return ReferenceRange(
        min=float(min_val) if min_val is not None else None,
        max=float(max_val) if max_val is not None else None,
        unit=unit,
    )
