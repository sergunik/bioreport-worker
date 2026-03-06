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
        _doc_id, doc_uuid, files_root = sample_pdf_on_disk
        processor = build_processor(test_settings, files_root=files_root)
        processor.process(doc_uuid, 1)

        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT parsed_result, anonymised_result,
                       anonymised_artifacts, transliteration_mapping,
                       normalized_result, final_result
                FROM uploaded_documents WHERE uuid = %s::uuid
                """,
                (doc_uuid,),
            )
            row = cur.fetchone()
        assert row is not None
        assert isinstance(row[0], str) and row[0].strip() != ""
        assert isinstance(row[1], str) and row[1].strip() != ""
        assert isinstance(row[2], dict) and "artifacts" in row[2]
        assert isinstance(row[3], list)
        assert isinstance(row[4], dict) and "person" in row[4]
        (
            _parsed_result,
            _anonymised_result,
            _anonymised_artifacts,
            _transliteration_mapping,
            _normalized_result,
            final_result,
        ) = row
        assert isinstance(final_result, dict) and "person" in final_result

    def test_process_raises_document_not_found(self, seed_job, test_settings: Settings) -> None:
        processor = build_processor(test_settings)
        with pytest.raises(DocumentNotFoundError):
            processor.process("00000000-0000-0000-0000-000000000000", seed_job.id)

    def test_process_raises_file_not_found(
        self,
        seed_document: tuple[int, str, int],
        seed_job,
        test_settings: Settings,
        files_root,
    ) -> None:
        _document_id, doc_uuid, _ = seed_document
        processor = build_processor(test_settings, files_root=files_root)
        with pytest.raises(FileNotFoundError):
            processor.process(doc_uuid, seed_job.id)
