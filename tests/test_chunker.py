from bot.chunker import chunk_text


def test_empty_input_returns_no_chunks() -> None:
    assert chunk_text("   \n\t  ", size=50, overlap=10) == []


def test_short_input_returns_single_chunk() -> None:
    text = "hello world"
    assert chunk_text(text, size=100, overlap=10) == [text]


def test_exact_boundary_returns_single_chunk() -> None:
    text = "a" * 20
    assert chunk_text(text, size=20, overlap=5) == [text]


def test_long_input_produces_multiple_overlapping_chunks() -> None:
    text = "abcdefghijklmnopqrstuvwxyz" * 5
    chunks = chunk_text(text, size=30, overlap=7)

    assert len(chunks) > 1
    for left, right in zip(chunks, chunks[1:]):
        suffix = left[-7:]
        assert suffix in right


def test_overlap_is_respected_for_hard_break_case() -> None:
    text = "x" * 100
    chunks = chunk_text(text, size=25, overlap=5)

    assert len(chunks) >= 3
    for left, right in zip(chunks, chunks[1:]):
        assert right.startswith(left[-5:])


def test_soft_break_prefers_paragraph_then_sentence() -> None:
    text = (
        "A" * 45
        + "\n\n"
        + "B" * 30
        + "."
        + "C" * 30
    )
    chunks = chunk_text(text, size=50, overlap=5)

    assert len(chunks) >= 2
    # Chunk is stripped, so paragraph separator is not present in output.
    # If soft break worked, first chunk should contain only the leading A-block.
    assert chunks[0] == "A" * 45
