from openai import OpenAI

from .config import settings


ANSWER_PROMPT = """You are a precise document assistant. Answer the user's question using ONLY the numbered chunks below. Reply in the same language as the question.

Rules:
1. After every factual statement, append an inline citation like [1] or [2,3] pointing to the chunk(s) it came from.
2. If the chunks do not contain the answer, OR if the question is empty, unclear, or unanswerable, reply with EXACTLY this single line and nothing else: I could not find this in the uploaded documents.
3. Do not invent information not present in the chunks. Do not editorialize, do not apologize, do not explain your limitations.

Chunks:
{chunks}

Question: {question}

Answer:"""


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": settings.app_url,
                "X-Title": settings.app_title,
            },
        )
    return _client


def answer(question: str, chunks: list[dict]) -> str:
    formatted_chunks = "\n\n".join(
        f"[{chunk['idx_in_prompt']}] {chunk['filename']} chunk {chunk['chunk_idx']}:\n{chunk['text']}"
        for chunk in chunks
    )
    prompt = ANSWER_PROMPT.format(chunks=formatted_chunks, question=question)
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.answer_model,
        max_tokens=settings.answer_max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        return "I could not find this in the uploaded documents."
    return content


def answer_stream(question: str, chunks: list[dict]):
    """Yield incremental text deltas for the answer prompt.

    Sync generator wrapping the OpenAI streaming chat API. Callers in async
    code should pump it via asyncio.to_thread per next().
    """
    formatted_chunks = "\n\n".join(
        f"[{chunk['idx_in_prompt']}] {chunk['filename']} chunk {chunk['chunk_idx']}:\n{chunk['text']}"
        for chunk in chunks
    )
    prompt = ANSWER_PROMPT.format(chunks=formatted_chunks, question=question)
    client = _get_client()
    stream = client.chat.completions.create(
        model=settings.answer_model,
        max_tokens=settings.answer_max_tokens,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for event in stream:
        if not event.choices:
            continue
        delta = getattr(event.choices[0].delta, "content", None) or ""
        if delta:
            yield delta


def complete(prompt: str, max_tokens: int | None = None) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.answer_model,
        max_tokens=max_tokens or settings.answer_max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()
