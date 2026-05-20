import sqlite3
from datetime import datetime, timezone

import sqlite_vec

from . import embeddings, llm
from .chunker import chunk_text
from .config import settings
from .db import get_conn


def ingest_document(user_id: int, filename: str, text: str) -> int:
    """Returns document_id."""
    if count_user_documents(user_id) >= settings.max_docs_per_user:
        raise ValueError(
            f"document limit reached ({settings.max_docs_per_user})"
        )

    chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise ValueError("no extractable text")
    if len(chunks) > settings.max_chunks_per_doc:
        raise ValueError(
            f"too many chunks ({len(chunks)} > {settings.max_chunks_per_doc})"
        )

    vectors = embeddings.embed(chunks)
    conn = get_conn()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO documents (user_id, filename, uploaded_at) VALUES (?, ?, ?)",
                (
                    user_id,
                    filename,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
            document_id = cursor.lastrowid
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors), start=1):
                chunk_cursor = conn.execute(
                    "INSERT INTO chunks (document_id, idx, text) VALUES (?, ?, ?)",
                    (document_id, idx, chunk),
                )
                conn.execute(
                    "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
                    (chunk_cursor.lastrowid, sqlite_vec.serialize_float32(vector)),
                )
        return int(document_id)
    finally:
        conn.close()


def answer_question(user_id: int, question: str) -> tuple[str, list[dict]]:
    """Returns (answer_text, sources)."""
    query_vector = embeddings.embed([question])[0]
    conn = get_conn()
    try:
        rows = _retrieve(conn, user_id, query_vector)
    finally:
        conn.close()

    if not rows:
        return 'I could not find this in the uploaded documents.', []

    chunks = [
        {
            "idx_in_prompt": i,
            "filename": row["filename"],
            "chunk_idx": row["chunk_idx"],
            "text": row["text"],
        }
        for i, row in enumerate(rows, start=1)
    ]
    answer_text = llm.answer(question, chunks)
    sources = [
        {
            "filename": chunk["filename"],
            "idx": chunk["chunk_idx"],
            "text_preview": chunk["text"][:180].replace("\n", " "),
        }
        for chunk in chunks
    ]
    return answer_text, sources


def count_user_documents(user_id: int) -> int:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def get_document_context(
    user_id: int, document_id: int | None = None, max_chunks: int = 8
) -> dict | None:
    """Return an owned document and its first chunks for source-grounded artifacts."""
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    try:
        if document_id is None:
            document = conn.execute(
                """
                SELECT id, filename, uploaded_at
                FROM documents
                WHERE user_id = ?
                ORDER BY uploaded_at DESC, id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        else:
            document = conn.execute(
                """
                SELECT id, filename, uploaded_at
                FROM documents
                WHERE user_id = ? AND id = ?
                """,
                (user_id, document_id),
            ).fetchone()
        if not document:
            return None

        chunks = conn.execute(
            """
            SELECT idx, text
            FROM chunks
            WHERE document_id = ?
            ORDER BY idx
            LIMIT ?
            """,
            (document["id"], max_chunks),
        ).fetchall()
    finally:
        conn.close()

    return {
        "document": dict(document),
        "chunks": [dict(chunk) for chunk in chunks],
    }


def _retrieve(
    conn: sqlite3.Connection, user_id: int, query_vector: list[float]
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """
        SELECT
            c.id,
            c.idx AS chunk_idx,
            c.text,
            d.filename,
            v.distance
        FROM vec_chunks AS v
        JOIN chunks AS c ON c.id = v.chunk_id
        JOIN documents AS d ON d.id = c.document_id
        WHERE v.embedding MATCH ?
          AND v.k = ?
          AND d.user_id = ?
        ORDER BY v.distance
        LIMIT ?
        """,
        (
            sqlite_vec.serialize_float32(query_vector),
            settings.top_k,
            user_id,
            settings.top_k,
        ),
    )
    return [dict(row) for row in cursor.fetchall()]
