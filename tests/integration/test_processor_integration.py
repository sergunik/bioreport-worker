from unittest.mock import patch

import pytest

pytest.importorskip("icu")

from app.config.settings import Settings
from app.processor.exceptions import DocumentNotFoundError
from app.processor.processor import build_processor


@pytest.mark.integration
class TestProcessorPipeline:
    def test_pipeline_to_step_4_persists_results(
        self,
        sample_pdf_on_disk: tuple[int, str, object],
        test_settings: Settings,
        db_conn,
    ) -> None:
        document_id, _doc_uuid, files_root = sample_pdf_on_disk
        processor = build_processor(test_settings, files_root=files_root)
        original_process = processor.process

        def process_without_raise(uploaded_document_id: int, job_id: int) -> None:
            try:
                original_process(uploaded_document_id, job_id)
            except NotImplementedError:
                pass

        with patch.object(processor, "process", process_without_raise):
            processor.process(document_id, 1)

        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT parsed_result, anonymised_result,
                       anonymised_artifacts, transliteration_mapping
                FROM uploaded_documents WHERE id = %s
                """,
                (document_id,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] is not None and len(row[0]) >= 0
        assert row[1] is not None
        assert row[2] is not None
        assert row[3] is not None

    def test_process_raises_document_not_found(self, seed_job, test_settings: Settings) -> None:
        processor = build_processor(test_settings)
        with pytest.raises(DocumentNotFoundError):
            processor.process(99999, seed_job.id)

    def test_process_raises_file_not_found(
        self,
        seed_document: tuple[int, str],
        seed_job,
        test_settings: Settings,
        files_root,
    ) -> None:
        document_id = seed_document[0]
        processor = build_processor(test_settings, files_root=files_root)
        with pytest.raises(FileNotFoundError):
            processor.process(document_id, seed_job.id)
