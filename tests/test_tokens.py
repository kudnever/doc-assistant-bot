from bot import tokens


def test_count_tokens_nonzero_for_nonempty_text() -> None:
    assert tokens.count_tokens("hello world") > 0


def test_count_tokens_zero_for_empty() -> None:
    assert tokens.count_tokens("") == 0


def test_pack_chunks_keeps_within_budget() -> None:
    chunks = [{"text": "word " * 50} for _ in range(10)]
    kept, dropped = tokens.pack_chunks(chunks, budget=120, per_chunk_overhead=0)
    total = sum(tokens.count_tokens(c["text"]) for c in kept)
    assert total <= 120
    assert dropped == len(chunks) - len(kept)
    assert dropped > 0, "expected some chunks to be dropped on a tight budget"


def test_pack_chunks_preserves_top_ranked() -> None:
    chunks = [{"text": f"chunk-{i} " + "x" * 40} for i in range(5)]
    kept, _ = tokens.pack_chunks(chunks, budget=60, per_chunk_overhead=0)
    assert kept and kept[0]["text"].startswith("chunk-0")


def test_pack_chunks_zero_budget_drops_all() -> None:
    chunks = [{"text": "any"}]
    kept, dropped = tokens.pack_chunks(chunks, budget=0)
    assert kept == [] and dropped == 1


def test_pack_chunks_empty_input() -> None:
    assert tokens.pack_chunks([], budget=100) == ([], 0)
