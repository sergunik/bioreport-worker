from dataclasses import dataclass, field


@dataclass(frozen=True)
class Artifact:
    """Single PII replacement record."""

    type: str  # e.g. "PERSON", "EMAIL", "PHONE", "ID"
    original: str  # original PII text
    replacement: str  # placeholder used in anonymized text, e.g. "PERSON_1"


@dataclass
class AnonymizationResult:
    """Output of the anonymizer step."""

    anonymized_text: str
    artifacts: list[Artifact] = field(default_factory=list)
    transliteration_mapping: list[int] = field(default_factory=list)
