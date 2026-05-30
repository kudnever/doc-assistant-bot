"""Token-aware chunk packing.

Uses tiktoken cl100k_base as a generic heuristic — exact token counts vary
per model, but cl100k is close enough to keep prompts under provider limits
across OpenAI, DeepSeek, Anthropic, and most OpenRouter models.
"""
from __future__ import annotations

import tiktoken

_ENCODING = None


def _enc() -> tiktoken.Encoding:
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_enc().encode(text, disallowed_special=()))


def pack_chunks(
    chunks: list[dict],
    budget: int,
    text_key: str = "text",
    per_chunk_overhead: int = 16,
) -> tuple[list[dict], int]:
    """Greedily keep chunks (in given order) under the token budget.

    `per_chunk_overhead` accounts for the small header line we add to each
    chunk inside the prompt (e.g. "[3] file.txt chunk 7:\\n").

    Returns (kept_chunks, dropped_count). Dropped chunks are tail-trimmed —
    we preserve the highest-ranked items.
    """
    if budget <= 0:
        return [], len(chunks)

    kept: list[dict] = []
    used = 0
    for chunk in chunks:
        cost = count_tokens(chunk.get(text_key, "")) + per_chunk_overhead
        if used + cost > budget:
            break
        kept.append(chunk)
        used += cost
    return kept, len(chunks) - len(kept)
