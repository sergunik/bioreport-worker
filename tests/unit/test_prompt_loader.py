"""Tests for prompt template and JSON schema loading."""

from pathlib import Path

import pytest

from app.normalization.exceptions import NormalizationError
from app.normalization.prompt_loader import load_json_schema, load_prompt_template


class TestLoadPromptTemplate:
    def test_loads_default_template(self) -> None:
        template = load_prompt_template()
        assert "{anonymized_text}" in template
        assert "{json_schema}" in template

    def test_loads_custom_template(self, tmp_path: Path) -> None:
        custom = tmp_path / "custom.txt"
        custom.write_text("Hello {anonymized_text}")
        result = load_prompt_template(custom)
        assert result == "Hello {anonymized_text}"

    def test_missing_file_raises_error(self) -> None:
        with pytest.raises(NormalizationError, match="Failed to load prompt"):
            load_prompt_template(Path("/nonexistent/file.txt"))


class TestLoadJsonSchema:
    def test_loads_default_schema(self) -> None:
        schema = load_json_schema()
        assert "person" in schema
        assert "markers" in schema

    def test_loads_custom_schema(self, tmp_path: Path) -> None:
        custom = tmp_path / "schema.json"
        custom.write_text('{"type": "object"}')
        result = load_json_schema(custom)
        assert result == '{"type": "object"}'

    def test_missing_file_raises_error(self) -> None:
        with pytest.raises(NormalizationError, match="Failed to load JSON schema"):
            load_json_schema(Path("/nonexistent/schema.json"))
