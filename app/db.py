"""A very small database layer.

It works with SQLite (a file, for your computer) and with PostgreSQL (for the real website).
All the SQL in the project is written so that both understand it:
  * placeholders are written as ?   (we change them to %s for PostgreSQL)
  * ids are random text (uuid), dates are text like 2026-11-14T10:25:00+00:00
"""
import sqlite3
import threading
from pathlib import Path

from app import config

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        premium_until TEXT,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS sessions_user ON sessions (user_id)",
    """CREATE TABLE IF NOT EXISTS usage (
        day TEXT NOT NULL,
        subject TEXT NOT NULL,
        uses INTEGER NOT NULL,
        PRIMARY KEY (day, subject)
    )""",
    # One row per Premium purchase. state: 0 new, 1 started (provider reserved it), 2 paid, -1 cancelled, -2 cancelled after paid.
    # Money is stored in tiyin (1 soum = 100 tiyin). Times are milliseconds since 1970.
    """CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        provider TEXT NOT NULL,
        days INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        state INTEGER NOT NULL,
        ptx_id TEXT,
        reason INTEGER,
        created_at TEXT NOT NULL,
        create_time BIGINT NOT NULL DEFAULT 0,
        perform_time BIGINT NOT NULL DEFAULT 0,
        cancel_time BIGINT NOT NULL DEFAULT 0
    )""",
    "CREATE INDEX IF NOT EXISTS orders_ptx ON orders (provider, ptx_id)",
]

_ready: set[str] = set()
_lock = threading.Lock()


def is_postgres(url: str | None = None) -> bool:
    return (url or config.DATABASE_URL).startswith(("postgres://", "postgresql://"))


def to_postgres_sql(sql: str) -> str:
    """SQLite writes ?  PostgreSQL writes %s."""
    return sql.replace("?", "%s")


def _sqlite_path(url: str) -> str:
    return url[len("sqlite:///"):] if url.startswith("sqlite:///") else url


def _open():
    url = config.DATABASE_URL
    if is_postgres(url):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as err:  # pragma: no cover (only on a server without the package)
            raise RuntimeError("DATABASE_URL points to PostgreSQL, but the package 'psycopg' is not installed.") from err
        return psycopg.connect(url, row_factory=dict_row)
    path = _sqlite_path(url)
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _run(conn, sql, params):
    if is_postgres():
        sql = to_postgres_sql(sql)
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def _ensure_schema() -> None:
    url = config.DATABASE_URL
    if url in _ready:
        return
    with _lock:
        if url in _ready:
            return
        conn = _open()
        try:
            for statement in SCHEMA:
                _run(conn, statement, ())
            conn.commit()
        finally:
            conn.close()
        _ready.add(url)


def execute(sql: str, params: tuple = ()) -> int:
    """Run INSERT / UPDATE / DELETE. Returns how many rows changed."""
    _ensure_schema()
    conn = _open()
    try:
        cur = _run(conn, sql, params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()) -> dict | None:
    _ensure_schema()
    conn = _open()
    try:
        row = _run(conn, sql, params).fetchone()
        return dict(row) if row is not None else None
    finally:
        conn.close()


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    _ensure_schema()
    conn = _open()
    try:
        return [dict(r) for r in _run(conn, sql, params).fetchall()]
    finally:
        conn.close()


def reset_for_tests() -> None:
    """Empty every table (used by the tests only)."""
    _ensure_schema()
    for table in ("sessions", "usage", "orders", "users"):
        execute(f"DELETE FROM {table}")
