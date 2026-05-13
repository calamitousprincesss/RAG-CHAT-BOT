from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from app.Config.settings import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    source TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    char_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    file_type TEXT NOT NULL DEFAULT 'text',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    expanded_query TEXT,
    strategy TEXT,
    answer TEXT,
    sources_json TEXT,
    latency_ms REAL,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def _conn():
    Path(settings.sqlite_full_path).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(settings.sqlite_full_path)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with _conn() as c:
        c.executescript(SCHEMA)


class DocumentModel:
    @staticmethod
    def insert(doc_id: str, filename: str, source: str, size_bytes: int,
               char_count: int, chunk_count: int, file_type: str = "text") -> None:
        with _conn() as c:
            c.execute("""INSERT INTO documents
                (id, filename, source, size_bytes, char_count, chunk_count, file_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, filename, source, size_bytes, char_count, chunk_count,
                 file_type, datetime.utcnow().isoformat()))

    @staticmethod
    def list_all() -> list[dict]:
        with _conn() as c:
            rows = c.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get(doc_id: str) -> dict | None:
        with _conn() as c:
            r = c.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            return dict(r) if r else None

    @staticmethod
    def delete(doc_id: str) -> None:
        with _conn() as c:
            c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

    @staticmethod
    def stats() -> dict:
        with _conn() as c:
            r = c.execute(
                "SELECT COUNT(*) AS docs, COALESCE(SUM(chunk_count),0) AS chunks, "
                "COALESCE(SUM(size_bytes),0) AS bytes FROM documents"
            ).fetchone()
            return dict(r)


class ChatSessionModel:
    @staticmethod
    def insert(query: str, expanded_query: str, strategy: str, answer: str,
               sources_json: str, latency_ms: float) -> int:
        with _conn() as c:
            cur = c.execute("""INSERT INTO chat_sessions
                (query, expanded_query, strategy, answer, sources_json, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (query, expanded_query, strategy, answer, sources_json,
                 latency_ms, datetime.utcnow().isoformat()))
            return cur.lastrowid

    @staticmethod
    def recent(limit: int = 20) -> list[dict]:
        with _conn() as c:
            rows = c.execute(
                "SELECT * FROM chat_sessions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def count() -> int:
        with _conn() as c:
            r = c.execute("SELECT COUNT(*) AS n FROM chat_sessions").fetchone()
            return r["n"]

    @staticmethod
    def avg_latency() -> float:
        with _conn() as c:
            r = c.execute("SELECT AVG(latency_ms) AS avg FROM chat_sessions").fetchone()
            return float(r["avg"] or 0)
