import httpx
import openai

from app.normalization.client_base import BaseNormalizationClient
from app.normalization.exceptions import NormalizationError, NormalizationNetworkError


class OpenAIClientAdapter(BaseNormalizationClient):
    """Normalization AI client adapter built on OpenAI-compatible chat API."""

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: int,
        base_url: str | None = None,
    ) -> None:
        self._client = openai.OpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            base_url=base_url,
        )

    def create_chat_completion(
        self,
        *,
        model: str,
        temperature: float,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, object],
    ) -> str:
        try:
            response = self._client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "normalization_result",
                        "strict": True,
                        "schema": json_schema,
                    },
                },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except (openai.APIConnectionError, httpx.ConnectError, httpx.TimeoutException) as exc:
            raise NormalizationNetworkError(
                f"AI provider network error: {exc}"
            ) from exc
        except openai.APIError as exc:
            raise NormalizationNetworkError(
                f"AI provider API error: {exc}"
            ) from exc

        if not response.choices:
            raise NormalizationError("AI returned no choices")
        content = response.choices[0].message.content
        if content is None:
            raise NormalizationError("AI returned empty response")
        return content
