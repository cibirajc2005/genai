"""SQLite locally, or Supabase Postgres when its connection URL is configured."""

import sqlite3
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from app.core.config import settings


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DatabaseConnection:
    """Normalizes the small SQL subset used by the routes across SQLite/Postgres."""

    def __init__(self, raw: Any, postgres: bool = False):
        self.raw = raw
        self.postgres = postgres

    def _sql(self, statement: str) -> str:
        return statement.replace("?", "%s") if self.postgres else statement

    def execute(self, statement: str, parameters: Any = ()):
        return self.raw.execute(self._sql(statement), parameters)

    def executemany(self, statement: str, parameters: Any):
        return self.raw.executemany(self._sql(statement), parameters)

    def executescript(self, script: str):
        return self.raw.executescript(script)


@contextmanager
def connection() -> Iterator[DatabaseConnection]:
    if settings.supabase_database_url:
        from psycopg import connect
        from psycopg.rows import dict_row

        # Transaction poolers used by serverless deployments do not support
        # prepared statements, so keep psycopg's automatic preparation disabled.
        raw = connect(
            settings.supabase_database_url,
            row_factory=dict_row,
            prepare_threshold=None,
        )
        try:
            yield DatabaseConnection(raw, postgres=True)
            raw.commit()
        finally:
            raw.close()
        return
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    try:
        yield DatabaseConnection(db)
        db.commit()
    finally:
        db.close()


def initialize_database() -> None:
    if settings.supabase_database_url:
        # The Supabase schema is installed from supabase/schema.sql. A small query
        # here makes configuration errors fail clearly during application startup.
        with connection() as db:
            db.execute("SELECT 1 FROM documents LIMIT 1")
        return
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, file_type TEXT NOT NULL,
          size INTEGER NOT NULL, status TEXT NOT NULL, department TEXT NOT NULL,
          content TEXT NOT NULL, path TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
          role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS query_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL,
          successful INTEGER NOT NULL, latency_ms INTEGER NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chunks (
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL, chunk_index INTEGER NOT NULL,
          content TEXT NOT NULL, vector TEXT NOT NULL, vector_model TEXT NOT NULL,
          created_at TEXT NOT NULL, FOREIGN KEY(document_id) REFERENCES documents(id)
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
        CREATE TABLE IF NOT EXISTS comparisons (
          id TEXT PRIMARY KEY, document_a_id TEXT NOT NULL, document_b_id TEXT NOT NULL,
          document_a_name TEXT NOT NULL, document_b_name TEXT NOT NULL,
          comparison TEXT NOT NULL, configured INTEGER NOT NULL, created_at TEXT NOT NULL
        );
        """)
        # Backfill vectors for documents uploaded before chunk storage existed.
        missing = db.execute("""SELECT d.id,d.content,d.created_at FROM documents d
            LEFT JOIN chunks c ON c.document_id=d.id GROUP BY d.id HAVING COUNT(c.id)=0""").fetchall()
        if missing:
            from app.services.documents import chunks
            from app.services.embeddings import local_embedding
            for document in missing:
                for index, content in enumerate(chunks(document["content"])):
                    db.execute("INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)", (
                        str(uuid.uuid4()), document["id"], index, content,
                        json.dumps(local_embedding(content)), "local-hash-384", document["created_at"]
                    ))
