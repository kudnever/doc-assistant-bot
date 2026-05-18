import pathlib
import tempfile

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from . import parsers, rag
from .config import settings
from .db import get_conn


router = Router()


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Send me a PDF, DOCX, or TXT file. Then ask any question about its content. "
        "/help for more, /list to see your uploads, /reset to delete all your data."
    )


@router.message(Command("help"))
async def help_(message: Message) -> None:
    await message.answer(
        "Upload a PDF, DOCX, or TXT file up to "
        f"{settings.max_file_mb} MB. I will extract the text, index it, and answer "
        "questions using only your uploaded documents. Answers include inline citations "
        "like [1] and a Sources footer."
    )


@router.message(Command("list"))
async def list_documents(message: Message) -> None:
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT filename, uploaded_at
            FROM documents
            WHERE user_id = ?
            ORDER BY uploaded_at DESC
            """,
            (message.from_user.id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        await message.answer("You have no uploaded documents.")
        return

    lines = [
        f"{i}. {filename} ({uploaded_at})"
        for i, (filename, uploaded_at) in enumerate(rows, start=1)
    ]
    await message.answer("\n".join(lines))


@router.message(Command("reset"))
async def reset(message: Message) -> None:
    conn = get_conn()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE user_id = ?",
            (message.from_user.id,),
        ).fetchone()[0]
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
                (message.from_user.id,),
            )
            conn.execute(
                "DELETE FROM documents WHERE user_id = ?",
                (message.from_user.id,),
            )
    finally:
        conn.close()

    await message.answer(f"Removed {count} document(s).")


@router.message(F.document)
async def upload_document(message: Message) -> None:
    document = message.document
    if document.file_size and document.file_size > settings.max_file_mb * 1024 * 1024:
        await message.answer(
            f"That file is too large. Please upload files up to {settings.max_file_mb} MB."
        )
        return

    suffix = pathlib.Path(document.file_name or "").suffix
    progress = await message.answer("⏳ Processing…")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = pathlib.Path(temp_file.name)
            await message.bot.download(document.file_id, destination=temp_file)

        text = parsers.extract_text(temp_path)
        document_id = rag.ingest_document(
            message.from_user.id, document.file_name or "document", text
        )
        chunk_count = _chunk_count(document_id)
        await progress.edit_text(
            f"Indexed {document.file_name or 'document'} into {chunk_count} chunk(s)."
        )
    except ValueError as exc:
        await progress.edit_text(str(exc))
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


@router.message(F.text)
async def question(message: Message) -> None:
    answer_text, sources = rag.answer_question(message.from_user.id, message.text)
    await message.answer(answer_text)
    if sources:
        footer = "\n".join(
            f"{i}. {source['filename']} chunk {source['idx']}"
            for i, source in enumerate(sources, start=1)
        )
        await message.answer(f"Sources:\n{footer}")


def _chunk_count(document_id: int) -> int:
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?",
            (document_id,),
        ).fetchone()[0]
    finally:
        conn.close()
