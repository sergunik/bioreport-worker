from app.config.settings import Settings
from app.logging.logger import Log


class Processor:
    """Linear pipeline: load -> extract -> anonymize -> normalize -> persist.

    Pipeline steps are added in subsequent tasks. This is the skeleton.
    """

    def process(self, uploaded_document_id: int, job_id: int) -> None:
        """Run the full processing pipeline for a document."""
        Log.info(f"Processing document {uploaded_document_id} for job {job_id}")


def build_processor(settings: Settings) -> Processor:
    """Build a Processor with all required adapters."""
    return Processor()
