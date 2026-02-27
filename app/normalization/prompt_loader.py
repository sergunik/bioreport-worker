from pathlib import Path

from app.normalization.exceptions import NormalizationError

_DEFAULT_PROMPT_DIR = Path(__file__).parent / "prompts"


def load_prompt_template(path: Path | None = None) -> str:
    """Load the normalization prompt template from a file.

    Args:
        path: Path to the prompt template file.
              Defaults to the bundled normalization_prompt.txt.

    Returns:
        The raw template string with placeholders.

    Raises:
        NormalizationError: if the file cannot be read.
    """
    if path is None:
        path = _DEFAULT_PROMPT_DIR / "normalization_prompt.txt"
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise NormalizationError(f"Failed to load prompt template: {exc}") from exc


def load_json_schema(path: Path | None = None) -> str:
    """Load the JSON schema template from a file.

    Args:
        path: Path to the JSON schema file.
              Defaults to the bundled normalization_schema.json.

    Returns:
        The raw JSON schema string.

    Raises:
        NormalizationError: if the file cannot be read.
    """
    if path is None:
        path = _DEFAULT_PROMPT_DIR / "normalization_schema.json"
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise NormalizationError(f"Failed to load JSON schema: {exc}") from exc
