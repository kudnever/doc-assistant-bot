from bot import query_expansion


def test_rrf_promotes_consistently_ranked_items() -> None:
    # "a" appears at rank 1 in two lists; "b" only at rank 1 in one.
    merged = query_expansion.rrf_merge([
        ["a", "b", "c"],
        ["a", "c", "b"],
        ["b", "a", "c"],
    ])
    assert merged[0] == "a"


def test_rrf_limit_truncates() -> None:
    merged = query_expansion.rrf_merge([["a", "b", "c", "d"]], limit=2)
    assert merged == ["a", "b"]


def test_rrf_handles_empty() -> None:
    assert query_expansion.rrf_merge([]) == []
    assert query_expansion.rrf_merge([[]]) == []


def test_expand_returns_original_first(monkeypatch) -> None:
    monkeypatch.setattr(query_expansion.llm, "complete",
                        lambda prompt, max_tokens=None: "alt one\nalt two\nalt three")
    out = query_expansion.expand("what is X?", n=3)
    assert out[0] == "what is X?"
    assert "alt one" in out
    assert len(out) == 4  # original + 3 paraphrases


def test_expand_dedupes_and_strips_bullets(monkeypatch) -> None:
    monkeypatch.setattr(query_expansion.llm, "complete",
                        lambda prompt, max_tokens=None: "- alt one\n1. alt one\n• alt two\n")
    out = query_expansion.expand("orig", n=3)
    assert out == ["orig", "alt one", "alt two"]


def test_expand_falls_back_on_llm_error(monkeypatch) -> None:
    def boom(prompt, max_tokens=None):
        raise RuntimeError("network down")
    monkeypatch.setattr(query_expansion.llm, "complete", boom)
    assert query_expansion.expand("orig", n=3) == ["orig"]


def test_expand_empty_input() -> None:
    assert query_expansion.expand("", n=3) == []
    assert query_expansion.expand("   ", n=3) == []
