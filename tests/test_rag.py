from pathlib import Path

import sqlite_vec

from bot import rag
from bot.config import settings
from bot.db import get_conn, init_schema


def _vec(dim: int) -> list[float]:
    return [0.1] * dim


def test_retrieval_isolation_by_user_id(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "rag.db"
    monkeypatch.setattr(settings, "db_path", str(db_path))
    monkeypatch.setattr(settings, "top_k", 10)
    monkeypatch.setattr(settings, "chunk_size", 10_000)
    monkeypatch.setattr(settings, "chunk_overlap", 10)

    dim = settings.embedding_dim

    def fake_embed(texts: list[str]) -> list[list[float]]:
        # Same vector for every text to force reliance on SQL user_id filtering.
        return [_vec(dim) for _ in texts]

    monkeypatch.setattr(rag.embeddings, "embed", fake_embed)
    monkeypatch.setattr(rag.llm, "answer", lambda question, chunks: "ok")

    conn = get_conn()
    try:
        init_schema(conn)
    finally:
        conn.close()

    rag.ingest_document(user_id=1, filename="u1_a.txt", text="alpha")
    rag.ingest_document(user_id=1, filename="u1_b.txt", text="beta")
    rag.ingest_document(user_id=2, filename="u2_private.txt", text="secret")

    answer, sources = rag.answer_question(user_id=1, question="anything")

    assert answer == "ok"
    assert len(sources) >= 1
    assert all(src["filename"] != "u2_private.txt" for src in sources)
    assert {src["filename"] for src in sources}.issubset({"u1_a.txt", "u1_b.txt"})


def test_retrieve_returns_no_rows_for_user_without_docs(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "rag-empty.db"
    monkeypatch.setattr(settings, "db_path", str(db_path))
    monkeypatch.setattr(settings, "top_k", 5)

    conn = get_conn()
    try:
        init_schema(conn)
        conn.execute(
            "INSERT INTO documents (user_id, filename, uploaded_at) VALUES (?, ?, datetime('now'))",
            (2, "u2.txt"),
        )
        doc_id = conn.execute("SELECT id FROM documents").fetchone()[0]
        conn.execute(
            "INSERT INTO chunks (document_id, idx, text) VALUES (?, ?, ?)",
            (doc_id, 1, "hello"),
        )
        chunk_id = conn.execute("SELECT id FROM chunks").fetchone()[0]
        conn.execute(
            "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
            (chunk_id, sqlite_vec.serialize_float32(_vec(settings.embedding_dim))),
        )
        conn.commit()

        rows = rag._retrieve(conn, user_id=1, query_vector=_vec(settings.embedding_dim))
    finally:
        conn.close()

    assert rows == []
