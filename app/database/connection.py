from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg_pool import ConnectionPool

from app.config.settings import Settings

_pool: ConnectionPool | None = None


def init_pool(settings: Settings) -> None:
    """Initialize the global connection pool from settings."""
    global _pool  # noqa: PLW0603
    conninfo = (
        f"host={settings.db_host} "
        f"port={settings.db_port} "
        f"dbname={settings.db_database} "
        f"user={settings.db_username} "
        f"password={settings.db_password}"
    )
    _pool = ConnectionPool(conninfo, min_size=1, max_size=10)


def close_pool() -> None:
    """Close the global connection pool."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_connection() -> Generator[psycopg.Connection[Any], None, None]:
    """Yield a connection from the pool. Caller manages commit/rollback."""
    if _pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    with _pool.connection() as conn:
        yield conn
