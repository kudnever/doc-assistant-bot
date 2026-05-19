import pathlib
import sqlite3

import sqlite_vec

from .config import settings


def get_conn() -> sqlite3.Connection:
    path = pathlib.Path(settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    # sqlite-vec requires the extension to be loaded on each new connection.
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    existing = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'vec_chunks'"
    ).fetchone()
    if existing and f"FLOAT[{settings.embedding_dim}]" not in existing[0]:
        import logging

        logging.getLogger("doc-assistant").warning(
            "vec_chunks dimension mismatch detected. Delete %s and restart to re-ingest with the new embedder.",
            settings.db_path,
        )

    conn.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            idx INTEGER NOT NULL,
            text TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_prefs (
            user_id INTEGER PRIMARY KEY,
            locale TEXT NOT NULL DEFAULT 'en'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding FLOAT[{settings.embedding_dim}]
        );
        """
    )
    conn.commit()


def get_locale(user_id: int) -> str:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT locale FROM user_prefs WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else "en"


def set_locale(user_id: int, locale: str) -> None:
    conn = get_conn()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO user_prefs (user_id, locale)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET locale = excluded.locale
                """,
                (user_id, locale),
            )
    finally:
        conn.close()
