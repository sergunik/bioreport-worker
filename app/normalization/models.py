from dataclasses import dataclass, field


@dataclass(frozen=True)
class NumericValue:
    """Numeric marker value."""

    type: str = "numeric"
    number: float = 0.0
    unit: str = ""


@dataclass(frozen=True)
class BooleanValue:
    """Boolean marker value."""

    type: str = "boolean"
    value: bool = False


@dataclass(frozen=True)
class TextValue:
    """Text marker value."""

    type: str = "text"
    text: str = ""


MarkerValue = NumericValue | BooleanValue | TextValue


@dataclass(frozen=True)
class ReferenceRange:
    """Reference range for a marker."""

    min: float | None = None
    max: float | None = None
    unit: str = ""


@dataclass(frozen=True)
class Marker:
    """A single medical marker measurement."""

    code: str
    name: str
    value: MarkerValue
    reference_range: ReferenceRange | None = None


@dataclass(frozen=True)
class Person:
    """Anonymized person information."""

    name: str
    dob: str | None = None


@dataclass(frozen=True)
class NormalizationResult:
    """Output of the normalization step."""

    person: Person
    diagnostic_date: str | None = None
    markers: list[Marker] = field(default_factory=list)
