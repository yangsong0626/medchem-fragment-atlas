from collections.abc import Iterator

import duckdb

from app.core.config import get_settings


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    settings = get_settings()
    settings.derived_dir.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(settings.database_path), read_only=read_only)


def get_connection() -> Iterator[duckdb.DuckDBPyConnection]:
    conn = connect(read_only=True)
    try:
        yield conn
    finally:
        conn.close()
