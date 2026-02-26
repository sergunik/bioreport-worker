from abc import ABC, abstractmethod


class BaseNormalizationClient(ABC):
    """Contract for provider-specific normalization AI clients."""

    @abstractmethod
    def create_chat_completion(
        self,
        *,
        model: str,
        temperature: float,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, object],
    ) -> str:
        """Return provider response as plain text."""
