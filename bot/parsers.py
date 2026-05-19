import pathlib
import zipfile

import docx
from pypdf import PdfReader

from .config import settings


class TooManyChunksError(ValueError):
    """Raised when the document would produce more chunks than allowed."""


class ZipBombError(ValueError):
    """Raised when a DOCX archive expands beyond the configured cap."""


def extract_text(path: pathlib.Path) -> str:
    if path.stat().st_size == 0:
        raise ValueError("empty file")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _pdf(path)
    elif suffix == ".docx":
        _check_zip_bomb(path)
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


def _check_zip_bomb(path: pathlib.Path) -> None:
    """Refuse DOCX files whose uncompressed payload exceeds the configured cap.

    A DOCX file is a ZIP archive. A small archive can declare a huge
    uncompressed payload; reading it would exhaust memory or disk. We sum the
    declared uncompressed sizes BEFORE extracting anything.
    """
    cap = settings.max_uncompressed_mb * 1024 * 1024
    try:
        with zipfile.ZipFile(path) as archive:
            total = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile as exc:
        raise ValueError("corrupt docx archive") from exc
    if total > cap:
        raise ZipBombError(
            f"docx expands to {total // (1024 * 1024)} MB, cap is "
            f"{settings.max_uncompressed_mb} MB"
        )
