from pathlib import Path

import pytest

from app.processor.exceptions import UnsupportedStorageDiskError
from app.processor.file_loader import FileLoader
from app.processor.models import UploadedDocument


def _make_document(
    storage_disk: str = "local",
    uuid: str = "abc-123",
) -> UploadedDocument:
    return UploadedDocument(
        id=1,
        uuid=uuid,
        user_id=10,
        storage_disk=storage_disk,
        file_hash_sha256="a" * 64,
        mime_type="application/pdf",
        file_size_bytes=1024,
    )


class TestLoadReturnsBytes:
    def test_returns_bytes_for_local_disk(self, tmp_path: Path) -> None:
        loader = FileLoader(files_root=tmp_path)
        doc = _make_document(storage_disk="local", uuid="abc-123")
        (tmp_path / "10" / "abc-123.pdf").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "10" / "abc-123.pdf").write_bytes(b"%PDF test content")

        result = loader.load(doc)

        assert result == b"%PDF test content"

    def test_reads_correct_file_by_uuid(self, tmp_path: Path) -> None:
        loader = FileLoader(files_root=tmp_path)
        doc = _make_document(uuid="def-456")
        (tmp_path / "10" / "def-456.pdf").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "10" / "def-456.pdf").write_bytes(b"%PDF other")

        result = loader.load(doc)

        assert result == b"%PDF other"


class TestLoadRaisesForS3:
    def test_raises_unsupported_storage_disk(self) -> None:
        loader = FileLoader(files_root=Path("/files"))
        doc = _make_document(storage_disk="s3")

        with pytest.raises(UnsupportedStorageDiskError, match="s3"):
            loader.load(doc)


class TestLoadRaisesWhenFileMissing:
    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        loader = FileLoader(files_root=tmp_path)
        doc = _make_document(storage_disk="local", uuid="missing")

        with pytest.raises(FileNotFoundError, match="missing"):
            loader.load(doc)
