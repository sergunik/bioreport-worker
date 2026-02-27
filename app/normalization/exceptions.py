class NormalizationError(Exception):
    """Raised when normalization fails."""


class NormalizationValidationError(NormalizationError):
    """Raised when the normalized result fails domain validation."""


class NormalizationNetworkError(NormalizationError):
    """Raised when the AI provider call fails due to network/infrastructure issues."""
