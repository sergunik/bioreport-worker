"""Example normalization client adapter.

Use this module as a reference when implementing new provider adapters.
Implement BaseNormalizationClient and register the provider in NormalizerFactory.
"""

import json
from typing import ClassVar

from app.normalization.client_base import BaseNormalizationClient


class ExampleClientAdapter(BaseNormalizationClient):
    """Example adapter that returns a fixed valid normalization JSON.

    No network calls. Useful for local development, tests, and as a template
    for building real provider adapters (OpenAI, Anthropic, etc.).
    """

    DEFAULT_RESPONSE: ClassVar[dict[str, object]] = {
        "person": {"name": "PERSON_1", "dob": None},
        "diagnostic_date": None,
        "markers": [],
    }

    def __init__(self) -> None:
        pass

    def create_chat_completion(
        self,
        *,
        model: str,
        temperature: float,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, object],
    ) -> str:
        _ = model, temperature, system_prompt, user_prompt, json_schema
        return json.dumps(self.DEFAULT_RESPONSE)
