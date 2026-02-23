from pathlib import Path

from app.processor.exceptions import UnsupportedStorageDiskError
from app.processor.models import UploadedDocument


class FileLoader:
    """Resolves filesystem path for a document and reads its bytes."""

    FILES_ROOT = Path("/app/files")

    def __init__(self, files_root: Path | None = None) -> None:
        self._files_root = files_root if files_root is not None else self.FILES_ROOT

    def load(self, document: UploadedDocument) -> bytes:
        """Read document bytes from disk.

        Raises:
            FileNotFoundError: if the file does not exist at resolved path.
            UnsupportedStorageDiskError: if storage_disk is not 'local'.
        """
        if document.storage_disk != "local":
            raise UnsupportedStorageDiskError(
                f"storage_disk '{document.storage_disk}' is not supported"
            )
        path = self._resolve_path(document)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_bytes()

    def _resolve_path(self, document: UploadedDocument) -> Path:
        """Build path: {files_root}/{uuid}.pdf"""
        return self._files_root / f"{document.uuid}.pdf"
