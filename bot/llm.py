import anthropic

from .config import settings


ANSWER_PROMPT = """You are a precise document assistant. Answer the user's question using ONLY the numbered chunks below. After each fact, add an inline citation like [1] or [2,3]. If the answer is not in the chunks, say "I could not find this in the uploaded documents." Do not invent.

Chunks:
{chunks}

Question: {question}

Answer:"""


def answer(question: str, chunks: list[dict]) -> str:
    formatted_chunks = "\n\n".join(
        f"[{chunk['idx_in_prompt']}] {chunk['filename']} chunk {chunk['chunk_idx']}:\n{chunk['text']}"
        for chunk in chunks
    )
    prompt = ANSWER_PROMPT.format(chunks=formatted_chunks, question=question)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.answer_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    ).strip()
