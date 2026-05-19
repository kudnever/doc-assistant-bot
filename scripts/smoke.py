import os
import pathlib


MISSING_OPENROUTER = not os.getenv("OPENROUTER_API_KEY")
os.environ.setdefault("BOT_TOKEN", "smoke-bot-token")
os.environ.setdefault("OPENROUTER_API_KEY", "smoke-openrouter-key")

from bot import llm, rag  # noqa: E402
from bot.config import settings  # noqa: E402
from bot.db import get_conn, init_schema  # noqa: E402


SAMPLE_TEXT = """
Acme Robotics was founded in 2017 in Pittsburgh by a team of warehouse automation engineers. The company started by building compact picking arms for regional fulfillment centers.

Its current products include the Finch mobile sorting robot, the AtlasBin inventory scanner, and a cloud dashboard for fleet health. Acme focuses on robots that can be installed without rebuilding an entire warehouse.

Acme Robotics has 142 employees across engineering, operations, customer success, and field support. The company opened a small Berlin support office in 2024 to serve European customers.

The CEO of Acme Robotics is Maya Chen. She previously led industrial automation programs for a large logistics company before joining Acme in 2021.
""".strip()


def main() -> int:
    if MISSING_OPENROUTER:
        llm.answer = _offline_answer

    db_path = pathlib.Path(settings.db_path)
    if db_path.exists():
        db_path.unlink()

    conn = get_conn()
    try:
        init_schema(conn)
    finally:
        conn.close()

    rag.ingest_document(user_id=999, filename="acme.txt", text=SAMPLE_TEXT)

    question_1 = "Who is the CEO of Acme Robotics?"
    answer_1, sources_1 = rag.answer_question(user_id=999, question=question_1)
    print(f"Q: {question_1}")
    print(f"A: {answer_1}")
    print(f"Sources: {sources_1}")
    print()

    question_2 = "What is the capital of France?"
    answer_2, sources_2 = rag.answer_question(user_id=999, question=question_2)
    print(f"Q: {question_2}")
    print(f"A: {answer_2}")
    print(f"Sources: {sources_2}")
    return 0


def _offline_answer(question: str, chunks: list[dict]) -> str:
    if "ceo" in question.lower() and any("Maya Chen" in chunk["text"] for chunk in chunks):
        return "The CEO of Acme Robotics is Maya Chen [1]."
    return "I could not find this in the uploaded documents."


if __name__ == "__main__":
    raise SystemExit(main())
