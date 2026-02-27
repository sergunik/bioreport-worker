import pytest

from app.database.repositories.uploaded_documents_repository import (
    UploadedDocumentsRepository,
)
from app.processor.exceptions import UnsupportedStorageDiskError
from app.processor.file_loader import FileLoader
from app.processor.models import UploadedDocument


@pytest.mark.integration
class TestFileLoaderLoad:
    def test_load_returns_pdf_bytes(
        self,
        sample_pdf_on_disk: tuple[int, str, object],
        sample_pdf_bytes: bytes,
    ) -> None:
        document_id, _doc_uuid, files_root = sample_pdf_on_disk
        repo = UploadedDocumentsRepository()
        document = repo.find_by_id(document_id)
        loader = FileLoader(files_root=files_root)
        result = loader.load(document)
        assert result == sample_pdf_bytes

    def test_load_raises_file_not_found(
        self, seed_document: tuple[int, str, int], files_root: object
    ) -> None:
        document_id, *_ = seed_document
        repo = UploadedDocumentsRepository()
        document = repo.find_by_id(document_id)
        loader = FileLoader(files_root=files_root)
        with pytest.raises(FileNotFoundError, match="File not found"):
            loader.load(document)

    def test_load_raises_unsupported_storage_disk(self) -> None:
        document = UploadedDocument(
            id=1,
            uuid="x",
            user_id=1,
            storage_disk="s3",
            file_hash_sha256="a" * 64,
            mime_type="application/pdf",
            file_size_bytes=0,
        )
        loader = FileLoader()
        with pytest.raises(
            UnsupportedStorageDiskError,
            match="storage_disk 's3' is not supported",
        ):
            loader.load(document)
