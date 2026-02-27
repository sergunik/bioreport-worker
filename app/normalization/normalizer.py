"""AI-powered medical data normalizer."""

import json
from pathlib import Path

from app.logging.logger import Log
from app.normalization.base import BaseNormalizer
from app.normalization.client_base import BaseNormalizationClient
from app.normalization.exceptions import NormalizationError
from app.normalization.models import NormalizationResult
from app.normalization.prompt_loader import load_json_schema, load_prompt_template
from app.normalization.validator import validate_and_build


class Normalizer(BaseNormalizer):
    """Normalizes anonymized medical text into structured data using an AI provider."""

    def __init__(
        self,
        *,
        client: BaseNormalizationClient,
        model: str,
        temperature: float = 0.0,
        prompt_template_path: Path | None = None,
        json_schema_path: Path | None = None,
        system_prompt: str = "",
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = max(0.0, min(0.2, temperature))
        self._system_prompt = system_prompt
        self._prompt_template = load_prompt_template(prompt_template_path)
        schema_str = load_json_schema(json_schema_path)
        self._json_schema = schema_str
        self._json_schema_dict = json.loads(schema_str)

    def normalize(self, text: str) -> NormalizationResult:
        """Transform anonymized medical text into structured data."""
        prompt = self._build_prompt(text)
        Log.debug(f"Normalization prompt:\n{prompt}")

        raw_response = self._call_ai(prompt)
        Log.debug(f"AI raw response:\n{raw_response}")

        parsed = self._parse_json(raw_response)
        result = validate_and_build(parsed)

        Log.info(f"Normalization complete: {len(result.markers)} markers extracted")
        return result

    def _build_prompt(self, text: str) -> str:
        return self._prompt_template.format(
            anonymized_text=text,
            json_schema=self._json_schema,
        )

    def _call_ai(self, prompt: str) -> str:
        return self._client.create_chat_completion(
            model=self._model,
            temperature=self._temperature,
            system_prompt=self._system_prompt,
            user_prompt=prompt,
            json_schema=self._json_schema_dict,
        )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, object]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise NormalizationError(f"Invalid JSON response: {exc}") from exc

        if not isinstance(parsed, dict):
            raise NormalizationError("JSON response must be an object")
        return parsed
