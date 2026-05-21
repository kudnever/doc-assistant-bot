"""Multi-query expansion for improved retrieval recall.

Issues one cheap LLM call to paraphrase the user's question into N variants,
then the retrieval layer embeds each variant and merges results via
Reciprocal Rank Fusion.

The expansion call is best-effort — any error falls back to a single-query
retrieval so a flaky LLM never blocks the user.
"""
from __future__ import annotations

import logging
from collections.abc import Hashable, Iterable

from . import llm


log = logging.getLogger("doc-assistant.query_expansion")


_EXPAND_PROMPT = """You rewrite a search query into alternative phrasings to improve document retrieval recall.

Return exactly {n} short alternative phrasings of the query below, one per line, no numbering, no commentary, in the same language as the query. Each line must be a self-contained search query.

Query: {question}"""


def expand(question: str, n: int = 3) -> list[str]:
    """Return [question, *paraphrases]. Always includes the original first."""
    question = (question or "").strip()
    if not question or n <= 0:
        return [question] if question else []

    try:
        raw = llm.complete(
            _EXPAND_PROMPT.format(n=n, question=question), max_tokens=256
        )
    except Exception as exc:  # noqa: BLE001 — boundary, must not fail user
        log.warning("query expansion failed, falling back: %s", exc)
        return [question]

    variants: list[str] = []
    seen = {question.lower()}
    for line in raw.splitlines():
        cleaned = line.strip().lstrip("-•0123456789. )").strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        variants.append(cleaned)
        if len(variants) >= n:
            break

    return [question, *variants]


def rrf_merge(
    ranked_lists: Iterable[Iterable[Hashable]],
    *,
    k: int = 60,
    limit: int | None = None,
) -> list[Hashable]:
    """Reciprocal Rank Fusion.

    Each input list is an ordered ranking of item identifiers (best first).
    Items get score = sum over lists of 1 / (k + rank_in_list), then sorted
    descending. Ties broken by first appearance order.
    """
    scores: dict[Hashable, float] = {}
    first_seen: dict[Hashable, int] = {}
    order = 0
    for ranking in ranked_lists:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
            if item not in first_seen:
                first_seen[item] = order
                order += 1

    merged = sorted(scores.keys(), key=lambda x: (-scores[x], first_seen[x]))
    if limit is not None:
        merged = merged[:limit]
    return merged
