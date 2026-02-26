from app.anonymization.models import AnonymizationResult, Artifact


class ArtifactsExtractor:
    """Converts anonymization artifacts to a JSON-serializable structure."""

    def extract(self, result: AnonymizationResult) -> dict[str, list[dict[str, str]]]:
        """Transform AnonymizationResult artifacts into JSONB-ready dict.

        Returns:
            Dict with 'artifacts' key containing list of artifact dicts.
        """
        return {
            "artifacts": [self._artifact_to_dict(a) for a in result.artifacts]
        }

    def _artifact_to_dict(self, artifact: Artifact) -> dict[str, str]:
        return {
            "type": artifact.type,
            "original": artifact.original,
            "replacement": artifact.replacement,
        }
