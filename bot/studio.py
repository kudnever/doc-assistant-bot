import json
import re
import secrets

from . import llm, rag


ARTIFACT_TITLES = {
    "overview": "DOCUMENT OVERVIEW",
    "brief": "BRIEFING DOC",
    "faq": "FAQ",
    "mindmap": "MIND MAP",
}

ARTIFACT_INSTRUCTIONS = {
    "overview": """Create a compact upload overview:
- 5-7 bullet summary
- key topics
- 5 useful questions the user can ask next
- any obvious risks, dates, obligations, or missing details""",
    "brief": """Create an executive briefing:
- what this document is about
- the most important facts
- decisions, obligations, dates, risks, and numbers if present
- concise next-step questions""",
    "faq": """Create 8-10 frequently asked questions and answers.
Each answer must be short, practical, and source-cited.""",
    "mindmap": """Create a readable text mind map using an indented tree.
Keep labels short and include citations on leaf nodes where factual.""",
}

QUIZ_PROMPT = """You are creating a source-grounded quiz from a document.
Use only the numbered source chunks. Return JSON only, with this exact shape:
{{
  "questions": [
    {{
      "question": "Question text?",
      "options": ["Option A", "Option B", "Option C"],
      "answer_index": 0,
      "explanation": "One sentence explaining the answer.",
      "citation": "[1]"
    }}
  ]
}}

Rules:
- Create 5 questions.
- Use 3 or 4 options per question.
- answer_index is zero-based.
- Every explanation must cite the source chunk in citation.
- Do not use markdown outside JSON.
- Reply in {language}.

Document: {filename}

Source chunks:
{chunks}
"""


def build_prompt(kind: str, locale: str, document: dict, chunks: list[dict]) -> str:
    if kind not in ARTIFACT_TITLES:
        raise ValueError(f"unknown studio artifact: {kind}")
    language = _language_name(locale)
    return f"""You are a precise document assistant.
Create this artifact: {ARTIFACT_TITLES[kind]}.

Instructions:
{ARTIFACT_INSTRUCTIONS[kind]}

Rules:
- Use only the numbered source chunks below.
- Cite factual claims with inline citations like [1] or [2,3].
- If the source chunks do not support a section, say that the document does not state it.
- Keep the output easy to scan in Telegram.
- Reply in {language}.

Document: {document["filename"]}

Source chunks:
{_format_chunks(chunks)}
"""


def generate_artifact(
    user_id: int,
    kind: str,
    locale: str,
    document_id: int | None = None,
) -> tuple[str, dict | None]:
    context = rag.get_document_context(user_id, document_id=document_id)
    if not context or not context["chunks"]:
        return "", None
    prompt = build_prompt(kind, locale, context["document"], context["chunks"])
    return llm.complete(prompt), context["document"]


def generate_quiz(
    user_id: int,
    locale: str,
    document_id: int | None = None,
) -> tuple[list[dict], dict | None]:
    context = rag.get_document_context(user_id, document_id=document_id)
    if not context or not context["chunks"]:
        return [], None
    prompt = QUIZ_PROMPT.format(
        language=_language_name(locale),
        filename=context["document"]["filename"],
        chunks=_format_chunks(context["chunks"]),
    )
    return parse_quiz_json(llm.complete(prompt)), context["document"]


def parse_quiz_json(raw: str) -> list[dict]:
    payload = _json_payload(raw)
    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("quiz must contain questions")

    parsed = []
    for item in questions:
        if not isinstance(item, dict):
            raise ValueError("quiz question must be an object")
        question = _required_string(item, "question")
        options = item.get("options")
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ValueError("quiz question must have 2-4 options")
        options = [_clean_option(option) for option in options]
        answer_index = item.get("answer_index")
        if not isinstance(answer_index, int) or not 0 <= answer_index < len(options):
            raise ValueError("quiz answer_index is out of range")
        parsed.append(
            {
                "question": question,
                "options": options,
                "answer_index": answer_index,
                "explanation": _required_string(item, "explanation"),
                "citation": _required_string(item, "citation"),
            }
        )
    return parsed


def fallback_overview(document: dict, chunks: list[dict]) -> str:
    filename = document["filename"]
    previews = []
    for chunk in chunks[:5]:
        first_sentence = _first_sentence(chunk["text"])
        if first_sentence:
            previews.append(f"- {first_sentence} [{chunk['idx']}]")
    preview_text = "\n".join(previews) if previews else "- Text was indexed successfully."
    return f"""Local overview for {filename}

The document was indexed and is ready for source-grounded questions. The LLM provider is rate-limited right now, so this quick overview is built locally from the first indexed sections.

Early sections:
{preview_text}

Try:
- /brief for an executive summary
- /faq for questions and answers
- /quiz for an interactive test
- /mindmap for a topic map"""


class QuizStore:
    def __init__(self):
        self._items: dict[str, dict] = {}

    def create(self, user_id: int, questions: list[dict], filename: str) -> str:
        token = secrets.token_hex(4)
        self._items[token] = {
            "user_id": user_id,
            "questions": questions,
            "filename": filename,
        }
        return token

    def get(self, token: str, user_id: int) -> dict | None:
        item = self._items.get(token)
        if not item or item["user_id"] != user_id:
            return None
        return item


def _format_chunks(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{chunk['idx']}] {chunk['text']}" for chunk in chunks)


def _json_payload(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("quiz response is not JSON")
    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("quiz response must be a JSON object")
    return payload


def _required_string(item: dict, key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"quiz field {key} must be a non-empty string")
    return value.strip()


def _clean_option(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("quiz options must be non-empty strings")
    return value.strip()


def _first_sentence(text: str) -> str:
    text = " ".join(text.split())
    if not text:
        return ""
    for separator in (". ", "? ", "! "):
        pos = text.find(separator)
        if 40 <= pos <= 220:
            return text[: pos + 1]
    return text[:220].rstrip()


def _language_name(locale: str) -> str:
    return {
        "ru": "Russian",
        "es": "Spanish",
        "de": "German",
        "fr": "French",
        "zh": "Chinese",
        "pt": "Portuguese",
    }.get(locale, "English")
