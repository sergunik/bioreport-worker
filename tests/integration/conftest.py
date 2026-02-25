import os
import uuid
from collections.abc import Generator
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from app.config.settings import Settings
from app.database.connection import close_pool, get_connection, init_pool
from app.database.models import JobRecord


def _test_settings() -> Settings:
    os.environ.setdefault("DB_DATABASE", "bioreport_test")
    return Settings()


def _choose_existing_account_id(db_conn: psycopg.Connection[Any]) -> tuple[int, str | None]:
    with db_conn.cursor() as cur:
        cur.execute("SELECT id, sensitive_words FROM accounts ORDER BY id LIMIT 1")
        row = cur.fetchone()
    if row is None:
        pytest.skip("No accounts rows in DB for integration test setup")
    return int(row[0]), row[1]


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return _test_settings()


@pytest.fixture(scope="session")
def integration_pool(test_settings: Settings) -> Generator[None, None, None]:
    try:
        init_pool(test_settings)
    except Exception as e:
        pytest.skip(
            f"PostgreSQL test DB not available: {e}. "
            "Set DB_* env or see tests/integration/README.md"
        )
    try:
        yield
    finally:
        close_pool()


@pytest.fixture
def db_conn(integration_pool: None) -> Generator[psycopg.Connection[Any], None, None]:
    with get_connection() as conn:
        yield conn


@pytest.fixture
def integration_cleanup() -> Generator[list[tuple[str, int]], None, None]:
    cleanup: list[tuple[str, int]] = []
    yield cleanup
    if not cleanup:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table, row_id in cleanup:
                if table == "pdf_jobs":
                    cur.execute("DELETE FROM pdf_jobs WHERE id = %s", (row_id,))
            for table, row_id in cleanup:
                if table == "uploaded_documents":
                    cur.execute("DELETE FROM uploaded_documents WHERE id = %s", (row_id,))
            for table, row_id in cleanup:
                if table == "accounts":
                    cur.execute("DELETE FROM accounts WHERE id = %s", (row_id,))
        conn.commit()


@pytest.fixture
def seed_document(
    db_conn: psycopg.Connection[Any],
    integration_cleanup: list[tuple[str, int]],
) -> tuple[int, str]:
    doc_uuid = str(uuid.uuid4())
    account_id, _ = _choose_existing_account_id(db_conn)
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO uploaded_documents
            (uuid, user_id, storage_disk, file_size_bytes, mime_type, file_hash_sha256)
            VALUES (%s::uuid, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (doc_uuid, account_id, "local", 1024, "application/pdf", "a" * 64),
        )
        row = cur.fetchone()
        assert row is not None
        document_id = row[0]
    db_conn.commit()
    integration_cleanup.append(("uploaded_documents", document_id))
    return (document_id, doc_uuid)


@pytest.fixture
def seed_job(
    db_conn: psycopg.Connection[Any],
    integration_cleanup: list[tuple[str, int]],
    seed_document: tuple[int, str],
) -> JobRecord:
    document_id = seed_document[0]
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO pdf_jobs (uploaded_document_id, status, attempts)
            VALUES (%s, 'pending', 0)
            RETURNING id, uploaded_document_id, status, attempts
            """,
            (document_id,),
        )
        row = cur.fetchone()
        assert row is not None
        job_id = row["id"]
    db_conn.commit()
    integration_cleanup.append(("pdf_jobs", job_id))
    return JobRecord(
        id=job_id,
        uploaded_document_id=document_id,
        status="pending",
        attempts=0,
    )


@pytest.fixture
def seed_account(
    db_conn: psycopg.Connection[Any],
) -> Generator[int, None, None]:
    account_id, previous_sensitive_words = _choose_existing_account_id(db_conn)
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE accounts SET sensitive_words = NULL WHERE id = %s",
            (account_id,),
        )
    db_conn.commit()
    try:
        yield account_id
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE accounts SET sensitive_words = %s WHERE id = %s",
                (previous_sensitive_words, account_id),
            )
        db_conn.commit()


@pytest.fixture
def seed_account_with_words(
    db_conn: psycopg.Connection[Any],
) -> Generator[int, None, None]:
    account_id, previous_sensitive_words = _choose_existing_account_id(db_conn)
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE accounts SET sensitive_words = %s WHERE id = %s",
            ("word1 word2", account_id),
        )
    db_conn.commit()
    try:
        yield account_id
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE accounts SET sensitive_words = %s WHERE id = %s",
                (previous_sensitive_words, account_id),
            )
        db_conn.commit()


@pytest.fixture
def files_root(tmp_path: Any) -> Any:
    return tmp_path


@pytest.fixture
def sample_pdf_on_disk(
    seed_document: tuple[int, str],
    files_root: Any,
    sample_pdf_bytes: bytes,
) -> tuple[int, str, Any]:
    document_id, doc_uuid = seed_document
    path = files_root / f"{doc_uuid}.pdf"
    path.write_bytes(sample_pdf_bytes)
    return (document_id, doc_uuid, files_root)
