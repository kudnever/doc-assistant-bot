from pathlib import Path
from types import SimpleNamespace

import sqlite_vec

from bot import llm, rag
from bot.config import settings
from bot.db import get_conn, init_schema


def _vec(dim: int) -> list[float]:
    return [0.1] * dim


def _make_stream(deltas):
    """Build a fake OpenAI-like streaming iterable from a list of text deltas."""
    for d in deltas:
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=d))]
        )


def test_answer_stream_yields_text_deltas(monkeypatch) -> None:
    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs.get("stream") is True
            return _make_stream(["Hello ", "world", "!"])

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    chunks = [{"idx_in_prompt": 1, "filename": "a.txt", "chunk_idx": 1, "text": "x"}]
    out = list(llm.answer_stream("q", chunks))

    assert out == ["Hello ", "world", "!"]


def test_answer_stream_skips_empty_choices(monkeypatch) -> None:
    def fake_stream():
        yield SimpleNamespace(choices=[])
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]
        )
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))]
        )

    class FakeCompletions:
        def create(self, **kwargs):
            return fake_stream()

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    chunks = [{"idx_in_prompt": 1, "filename": "a.txt", "chunk_idx": 1, "text": "x"}]
    assert list(llm.answer_stream("q", chunks)) == ["ok"]


def test_answer_question_stream_returns_sources_and_iter(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "rag-stream.db"
    monkeypatch.setattr(settings, "db_path", str(db_path))
    monkeypatch.setattr(settings, "top_k", 5)
    monkeypatch.setattr(settings, "chunk_size", 10_000)
    monkeypatch.setattr(settings, "chunk_overlap", 10)

    dim = settings.embedding_dim
    monkeypatch.setattr(rag.embeddings, "embed", lambda texts: [_vec(dim) for _ in texts])
    monkeypatch.setattr(
        rag.llm, "answer_stream",
        lambda question, chunks: iter(["streamed ", "answer"]),
    )

    conn = get_conn()
    try:
        init_schema(conn)
    finally:
        conn.close()

    rag.ingest_document(user_id=1, filename="a.txt", text="alpha doc")

    sources, stream = rag.answer_question_stream(user_id=1, question="q")

    assert sources and sources[0]["filename"] == "a.txt"
    assert "".join(stream) == "streamed answer"


def test_answer_question_stream_empty_when_no_documents(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "rag-stream-empty.db"
    monkeypatch.setattr(settings, "db_path", str(db_path))
    dim = settings.embedding_dim
    monkeypatch.setattr(rag.embeddings, "embed", lambda texts: [_vec(dim) for _ in texts])

    conn = get_conn()
    try:
        init_schema(conn)
    finally:
        conn.close()

    sources, stream = rag.answer_question_stream(user_id=1, question="q")
    assert sources == []
    assert "could not find" in "".join(stream).lower()
