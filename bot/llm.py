from openai import OpenAI

from .config import settings


ANSWER_PROMPT = """You are a precise document assistant. Answer the user's question using ONLY the numbered chunks below. After each fact, add an inline citation like [1] or [2,3]. If the answer is not in the chunks, say "I could not find this in the uploaded documents." Do not invent.

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
    return (response.choices[0].message.content or "").strip()
