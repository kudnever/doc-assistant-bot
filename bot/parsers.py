import pathlib

import docx
from pypdf import PdfReader


def extract_text(path: pathlib.Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _pdf(path)
    elif suffix == ".docx":
        text = _docx(path)
    elif suffix == ".txt":
        text = path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"unsupported file type: {suffix}")

    if not text.strip():
        raise ValueError("no extractable text")
    return text


def _pdf(path: pathlib.Path) -> str:
    reader = PdfReader(path)
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _docx(path: pathlib.Path) -> str:
    document = docx.Document(path)
    return "\n\n".join(paragraph.text for paragraph in document.paragraphs)
