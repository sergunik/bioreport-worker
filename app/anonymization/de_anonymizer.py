"""Replaces anonymization placeholders with original values in structured data."""

from typing import Any

from app.anonymization.models import Artifact


def de_anonymize_payload(
    payload: dict[str, Any],
    artifacts: list[Artifact],
) -> dict[str, Any]:
    """Replace all anonymization placeholders in a dict with original PII values.

    Traverses the payload recursively and substitutes every occurrence of
    each artifact's replacement placeholder with its original text.

    Args:
        payload: Normalized JSON dict (may contain nested dicts/lists/strings).
        artifacts: Anonymization artifacts mapping replacements to originals.

    Returns:
        A new dict with all placeholders replaced.
    """
    if not artifacts:
        result = _replace_in_value(payload, [])
        assert isinstance(result, dict)
        return result
    replacements = {a.replacement: a.original for a in artifacts}
    sorted_pairs = sorted(
        replacements.items(),
        key=lambda p: len(p[0]),
        reverse=True,
    )
    result = _replace_in_value(payload, sorted_pairs)
    assert isinstance(result, dict)
    return result


def _replace_in_value(value: Any, replacements: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        for placeholder, original in replacements:
            value = value.replace(placeholder, original)
        return value
    if isinstance(value, dict):
        return {k: _replace_in_value(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_in_value(item, replacements) for item in value]
    return value
