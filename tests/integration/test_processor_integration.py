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
        try:
            processor.process(document_id, 1)
        except NotImplementedError:
            pass

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
        assert isinstance(row[0], str) and row[0].strip() != ""
        assert isinstance(row[1], str) and row[1].strip() != ""
        assert isinstance(row[2], dict) and "artifacts" in row[2]
        assert isinstance(row[3], list)

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
