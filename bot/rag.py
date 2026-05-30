import sqlite3
from datetime import datetime, timezone

import logging

import sqlite_vec

from . import embeddings, llm, query_expansion, tokens
from .chunker import chunk_text
from .config import settings
from .db import get_conn


log = logging.getLogger("doc-assistant.rag")


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


def answer_question(
    user_id: int,
    question: str,
    document_id: int | None = None,
) -> tuple[str, list[dict]]:
    """Returns (answer_text, sources).

    When document_id is given, retrieval is scoped to that single document
    (still enforcing user_id ownership). Otherwise retrieval spans all
    documents owned by the user.
    """
    queries = (
        query_expansion.expand(question, n=settings.multi_query_variants)
        if settings.multi_query_enabled
        else [question]
    )
    query_vectors = embeddings.embed(queries) if queries else []
    conn = get_conn()
    try:
        rows = _retrieve_multi(
            conn, user_id, query_vectors, document_id=document_id
        )
    finally:
        conn.close()

    if not rows:
        return 'I could not find this in the uploaded documents.', []

    chunks = [
        {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "chunk_idx": row["chunk_idx"],
            "text": row["text"],
        }
        for row in rows
    ]
    chunks, dropped = tokens.pack_chunks(
        chunks, budget=settings.answer_context_budget_tokens
    )
    if dropped:
        log.info(
            "answer prompt trimmed: kept=%d dropped=%d budget=%d",
            len(chunks),
            dropped,
            settings.answer_context_budget_tokens,
        )
    if not chunks:
        return 'I could not find this in the uploaded documents.', []
    for i, chunk in enumerate(chunks, start=1):
        chunk["idx_in_prompt"] = i
    answer_text = llm.answer(question, chunks)
    sources = [
        {
            "document_id": chunk["document_id"],
            "filename": chunk["filename"],
            "idx": chunk["chunk_idx"],
            "text_preview": chunk["text"][:180].replace("\n", " "),
        }
        for chunk in chunks
    ]
    return answer_text, sources


def answer_question_stream(
    user_id: int,
    question: str,
    document_id: int | None = None,
):
    """Streaming variant of answer_question.

    Returns (sources, stream_iter). The iterator yields incremental text
    deltas from the LLM. Sources are computed up-front from retrieval and
    are stable across the stream.

    When retrieval returns nothing, sources is [] and stream_iter yields
    the single "not found" sentinel so the caller can render it uniformly.
    """
    queries = (
        query_expansion.expand(question, n=settings.multi_query_variants)
        if settings.multi_query_enabled
        else [question]
    )
    query_vectors = embeddings.embed(queries) if queries else []
    conn = get_conn()
    try:
        rows = _retrieve_multi(
            conn, user_id, query_vectors, document_id=document_id
        )
    finally:
        conn.close()

    if not rows:
        return [], iter(["I could not find this in the uploaded documents."])

    chunks = [
        {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "chunk_idx": row["chunk_idx"],
            "text": row["text"],
        }
        for row in rows
    ]
    chunks, dropped = tokens.pack_chunks(
        chunks, budget=settings.answer_context_budget_tokens
    )
    if dropped:
        log.info(
            "answer prompt trimmed: kept=%d dropped=%d budget=%d",
            len(chunks),
            dropped,
            settings.answer_context_budget_tokens,
        )
    if not chunks:
        return [], iter(["I could not find this in the uploaded documents."])

    for i, chunk in enumerate(chunks, start=1):
        chunk["idx_in_prompt"] = i

    sources = [
        {
            "document_id": chunk["document_id"],
            "filename": chunk["filename"],
            "idx": chunk["chunk_idx"],
            "text_preview": chunk["text"][:180].replace("\n", " "),
        }
        for chunk in chunks
    ]
    return sources, llm.answer_stream(question, chunks)


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


def _retrieve_multi(
    conn: sqlite3.Connection,
    user_id: int,
    query_vectors: list[list[float]],
    document_id: int | None = None,
) -> list[dict]:
    """Retrieve across multiple query embeddings and fuse via RRF.

    Falls back to plain single-query retrieval when given <=1 vectors.
    """
    if not query_vectors:
        return []
    if len(query_vectors) == 1:
        return _retrieve(conn, user_id, query_vectors[0], document_id=document_id)

    rankings: list[list[int]] = []
    by_id: dict[int, dict] = {}
    for vec in query_vectors:
        rows = _retrieve(conn, user_id, vec, document_id=document_id)
        rankings.append([row["id"] for row in rows])
        for row in rows:
            by_id.setdefault(row["id"], row)

    fused_ids = query_expansion.rrf_merge(rankings, limit=settings.top_k)
    return [by_id[cid] for cid in fused_ids if cid in by_id]


def _retrieve(
    conn: sqlite3.Connection,
    user_id: int,
    query_vector: list[float],
    document_id: int | None = None,
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    # sqlite-vec's KNN runs before the SQL WHERE filters, so requesting
    # exactly top_k can return zero rows when other users dominate the index.
    # Over-fetch and let the user/doc filters trim down to top_k.
    knn_k = max(settings.top_k * 8, 32)
    base_sql = """
        SELECT
            c.id,
            c.idx AS chunk_idx,
            c.text,
            c.document_id AS document_id,
            d.filename,
            v.distance
        FROM vec_chunks AS v
        JOIN chunks AS c ON c.id = v.chunk_id
        JOIN documents AS d ON d.id = c.document_id
        WHERE v.embedding MATCH ?
          AND v.k = ?
          AND d.user_id = ?
    """
    params: list = [
        sqlite_vec.serialize_float32(query_vector),
        knn_k,
        user_id,
    ]
    if document_id is not None:
        base_sql += " AND d.id = ?"
        params.append(document_id)
    base_sql += " ORDER BY v.distance LIMIT ?"
    params.append(settings.top_k)

    cursor = conn.execute(base_sql, params)
    return [dict(row) for row in cursor.fetchall()]
