import html
import pathlib
import tempfile
from datetime import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from . import db, keyboards, parsers, rag
from .config import settings
from .i18n import LOCALES, t


router = Router()


async def _safe_edit_text(message, text, **kwargs):
    """Edit a message, swallowing the harmless 'message is not modified' 400."""
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise

RU_MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

EN_MONTHS = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


@router.message(Command("start"))
async def start(message: Message) -> None:
    user_id = message.from_user.id
    locale = db.get_locale(user_id)
    await message.answer(
        _welcome_text(locale),
        reply_markup=keyboards.welcome_keyboard(locale),
    )


@router.message(Command("help"))
async def help_(message: Message) -> None:
    user_id = message.from_user.id
    locale = db.get_locale(user_id)
    await message.answer(t("help", locale, max_file_mb=settings.max_file_mb))


@router.message(Command("list"))
async def list_documents(message: Message) -> None:
    user_id = message.from_user.id
    locale = db.get_locale(user_id)
    documents = _documents(user_id)
    await message.answer(
        _documents_text(user_id, locale, documents),
        reply_markup=keyboards.documents_keyboard(documents, locale)
        if documents
        else None,
    )


@router.message(Command("settings"))
async def settings_(message: Message) -> None:
    user_id = message.from_user.id
    locale = db.get_locale(user_id)
    await message.answer(
        _settings_text(user_id, locale),
        reply_markup=keyboards.settings_keyboard(locale),
    )


@router.message(Command("reset"))
async def reset(message: Message) -> None:
    user_id = message.from_user.id
    locale = db.get_locale(user_id)
    counts = _account_counts(user_id)
    await message.answer(
        t(
            "reset_confirm",
            locale,
            doc_count=counts["doc_count"],
            chunk_count=counts["chunk_count"],
        ),
        reply_markup=keyboards.reset_confirm_keyboard(locale),
    )


@router.message(F.document)
async def upload_document(message: Message) -> None:
    user_id = message.from_user.id
    locale = db.get_locale(user_id)
    document = message.document
    filename = document.file_name or t("default_filename", locale)
    safe_filename = html.escape(filename)
    progress = await message.answer(t("processing", locale, filename=safe_filename))

    if document.file_size and document.file_size > settings.max_file_mb * 1024 * 1024:
        await progress.edit_text(
            t(
                "upload_error",
                locale,
                filename=safe_filename,
                error_reason=t(
                    "error_too_large",
                    locale,
                    max_file_mb=settings.max_file_mb,
                ),
            )
        )
        return

    suffix = pathlib.Path(filename).suffix
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = pathlib.Path(temp_file.name)
            await message.bot.download(document.file_id, destination=temp_file)

        text = parsers.extract_text(temp_path)
        document_id = rag.ingest_document(user_id, filename, text)
        chunk_count = _chunk_count(document_id)
        await progress.edit_text(
            t(
                "indexed",
                locale,
                filename=safe_filename,
                chunk_count=chunk_count,
            )
        )
    except ValueError as exc:
        await progress.edit_text(
            t(
                "upload_error",
                locale,
                filename=safe_filename,
                error_reason=_upload_error_reason(str(exc), locale),
            )
        )
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


@router.message(F.text & ~F.text.startswith("/"))
async def question(message: Message) -> None:
    user_id = message.from_user.id
    locale = db.get_locale(user_id)
    try:
        answer_text, sources = rag.answer_question(user_id, message.text)
    except Exception:
        await message.answer(t("rate_limited", locale))
        return

    if _not_found(answer_text):
        await message.answer(t("answer_not_found", locale))
        return

    await message.answer(_answer_text(answer_text, sources, locale))


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    locale = callback.data.split(":", 1)[1]
    if locale not in LOCALES:
        await callback.answer()
        return

    db.set_locale(user_id, locale)
    message_text = ""
    if callback.message:
        message_text = callback.message.html_text or callback.message.text or ""

    if callback.message and _is_settings_message(message_text):
        await _safe_edit_text(callback.message,
            _settings_text(user_id, locale),
            reply_markup=keyboards.settings_keyboard(locale),
        )
    elif callback.message:
        await _safe_edit_text(callback.message,
            _welcome_text(locale),
            reply_markup=keyboards.welcome_keyboard(locale),
        )
    await callback.answer()


@router.callback_query(F.data == "settings")
async def open_settings(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    locale = db.get_locale(user_id)
    if callback.message:
        await callback.message.answer(
            _settings_text(user_id, locale),
            reply_markup=keyboards.settings_keyboard(locale),
        )
    await callback.answer()


@router.callback_query(F.data == "settings:close")
async def close_settings(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "settings:reset")
async def open_reset_confirm(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    locale = db.get_locale(user_id)
    counts = _account_counts(user_id)
    if callback.message:
        await _safe_edit_text(callback.message,
            t(
                "reset_confirm",
                locale,
                doc_count=counts["doc_count"],
                chunk_count=counts["chunk_count"],
            ),
            reply_markup=keyboards.reset_confirm_keyboard(locale),
        )
    await callback.answer()


@router.callback_query(F.data == "reset:yes")
async def confirm_reset(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    locale = db.get_locale(user_id)
    _delete_all_user_data(user_id)
    if callback.message:
        await _safe_edit_text(callback.message,t("reset_done", locale))
    await callback.answer()


@router.callback_query(F.data == "reset:no")
async def cancel_reset(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    locale = db.get_locale(user_id)
    if callback.message:
        await _safe_edit_text(callback.message,
            _settings_text(user_id, locale),
            reply_markup=keyboards.settings_keyboard(locale),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("del:"))
async def open_delete_document(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    locale = db.get_locale(user_id)
    doc_id = int(callback.data.split(":", 1)[1])
    document = _document(user_id, doc_id)
    if callback.message and document:
        await _safe_edit_text(callback.message,
            t(
                "delete_confirm",
                locale,
                filename=html.escape(str(document["filename"])),
                date=_format_date(str(document["uploaded_at"]), locale),
                chunk_count=document["chunk_count"],
            ),
            reply_markup=keyboards.delete_confirm_keyboard(doc_id, locale),
        )
    elif callback.message:
        await _edit_documents_message(callback.message, user_id, locale)
    await callback.answer()


@router.callback_query(F.data.startswith("delc:"))
async def confirm_delete_document(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    locale = db.get_locale(user_id)
    doc_id = int(callback.data.split(":", 1)[1])
    _delete_document(user_id, doc_id)
    if callback.message:
        await _edit_documents_message(callback.message, user_id, locale)
    await callback.answer()


@router.callback_query(F.data == "delx")
async def cancel_delete_document(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    locale = db.get_locale(user_id)
    if callback.message:
        await _edit_documents_message(callback.message, user_id, locale)
    await callback.answer()


def _welcome_text(locale: str) -> str:
    return t("welcome", locale, max_file_mb=settings.max_file_mb)


def _answer_text(answer_text: str, sources: list[dict], locale: str) -> str:
    source_lines = [
        t(
            "source_line",
            locale,
            number=i,
            filename=html.escape(str(source["filename"])),
            idx=source["idx"],
        )
        for i, source in enumerate(sources, start=1)
    ]
    return t(
        "answer_message",
        locale,
        answer=html.escape(answer_text),
        sources="\n".join(source_lines),
    )


async def _edit_documents_message(message: Message, user_id: int, locale: str) -> None:
    documents = _documents(user_id)
    await _safe_edit_text(
        message,
        _documents_text(user_id, locale, documents),
        reply_markup=keyboards.documents_keyboard(documents, locale)
        if documents
        else None,
    )


def _documents_text(
    user_id: int, locale: str, documents: list[dict] | None = None
) -> str:
    if documents is None:
        documents = _documents(user_id)
    if not documents:
        return t("list_empty", locale)

    lines = [t("list_header", locale)]
    for i, document in enumerate(documents, start=1):
        lines.append("")
        lines.append(
            t(
                "list_item",
                locale,
                number=i,
                filename=html.escape(str(document["filename"])),
                date=_format_date(str(document["uploaded_at"]), locale),
                chunk_count=document["chunk_count"],
            )
        )
    return "\n".join(lines)


def _settings_text(user_id: int, locale: str) -> str:
    counts = _account_counts(user_id)
    return t(
        "settings",
        locale,
        locale_name=_locale_name(locale),
        doc_count=counts["doc_count"],
        chunk_count=counts["chunk_count"],
    )


def _documents(user_id: int) -> list[dict]:
    conn = db.get_conn()
    conn.row_factory = db.sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                d.id,
                d.filename,
                d.uploaded_at,
                COUNT(c.id) AS chunk_count
            FROM documents AS d
            LEFT JOIN chunks AS c ON c.document_id = d.id
            WHERE d.user_id = ?
            GROUP BY d.id
            ORDER BY d.uploaded_at DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def _document(user_id: int, doc_id: int) -> dict | None:
    conn = db.get_conn()
    conn.row_factory = db.sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT
                d.id,
                d.filename,
                d.uploaded_at,
                COUNT(c.id) AS chunk_count
            FROM documents AS d
            LEFT JOIN chunks AS c ON c.document_id = d.id
            WHERE d.user_id = ? AND d.id = ?
            GROUP BY d.id
            """,
            (user_id, doc_id),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _delete_document(user_id: int, doc_id: int) -> None:
    conn = db.get_conn()
    try:
        with conn:
            conn.execute(
                """
                DELETE FROM vec_chunks
                WHERE chunk_id IN (
                    SELECT c.id
                    FROM chunks AS c
                    JOIN documents AS d ON d.id = c.document_id
                    WHERE d.user_id = ? AND d.id = ?
                )
                """,
                (user_id, doc_id),
            )
            conn.execute(
                "DELETE FROM documents WHERE user_id = ? AND id = ?",
                (user_id, doc_id),
            )
    finally:
        conn.close()


def _delete_all_user_data(user_id: int) -> None:
    conn = db.get_conn()
    try:
        with conn:
            conn.execute(
                """
                DELETE FROM vec_chunks
                WHERE chunk_id IN (
                    SELECT c.id
                    FROM chunks AS c
                    JOIN documents AS d ON d.id = c.document_id
                    WHERE d.user_id = ?
                )
                """,
                (user_id,),
            )
            conn.execute(
                "DELETE FROM documents WHERE user_id = ?",
                (user_id,),
            )
    finally:
        conn.close()


def _account_counts(user_id: int) -> dict[str, int]:
    conn = db.get_conn()
    try:
        doc_count = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        chunk_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM chunks AS c
            JOIN documents AS d ON d.id = c.document_id
            WHERE d.user_id = ?
            """,
            (user_id,),
        ).fetchone()[0]
    finally:
        conn.close()
    return {"doc_count": doc_count, "chunk_count": chunk_count}


def _chunk_count(document_id: int) -> int:
    conn = db.get_conn()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?",
            (document_id,),
        ).fetchone()[0]
    finally:
        conn.close()


def _upload_error_reason(error: str, locale: str) -> str:
    if error.startswith("unsupported file type"):
        return t("error_unsupported_format", locale)
    if error == "no extractable text":
        return t("error_no_text", locale)
    if error == "empty file":
        return t("error_empty_file", locale)
    if error.startswith("too many chunks"):
        return t(
            "error_too_many_chunks",
            locale,
            max_chunks_per_doc=settings.max_chunks_per_doc,
        )
    if error.startswith("document limit reached"):
        return t(
            "error_too_many_docs",
            locale,
            max_docs_per_user=settings.max_docs_per_user,
        )
    if error.startswith("docx expands"):
        return t("error_zip_bomb", locale)
    if error == "corrupt docx archive":
        return t("error_corrupt_docx", locale)
    return html.escape(error)


def _not_found(answer_text: str) -> bool:
    return answer_text.strip() == "I could not find this in the uploaded documents."


def _locale_name(locale: str) -> str:
    return t(f"locale_name_{locale}", locale)


_SETTINGS_HEADERS_HTML = tuple(
    f"<b>{t('button_settings', loc)}</b>" for loc in LOCALES
)
_SETTINGS_HEADERS_PLAIN = tuple(t("button_settings", loc) for loc in LOCALES)


def _is_settings_message(text: str) -> bool:
    return text.startswith(_SETTINGS_HEADERS_HTML) or text.startswith(_SETTINGS_HEADERS_PLAIN)


def _format_date(value: str, locale: str) -> str:
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    months = RU_MONTHS if locale == "ru" else EN_MONTHS
    return f"{date.day} {months[date.month]} {date.year}"
