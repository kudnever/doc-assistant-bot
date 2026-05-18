def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("chunk overlap must be non-negative and smaller than size")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        hard_end = min(start + size, len(text))
        end = _soft_break(text, start, hard_end, size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return chunks


def _soft_break(text: str, start: int, hard_end: int, size: int) -> int:
    if hard_end >= len(text):
        return hard_end

    soft_start = start + int(size * 0.8)
    window = text[soft_start:hard_end]
    for separator in ("\n\n", "\n", "."):
        pos = window.rfind(separator)
        if pos != -1:
            return soft_start + pos + len(separator)
    return hard_end
