"""Inline keyboard factories.

Callback data prefixes:
lang:<en|ru> - set locale
settings - open settings panel
settings:close - close settings
settings:reset - open reset confirm
reset:yes / reset:no - confirm/cancel full reset
del:<doc_id> - open per-document delete confirm
delc:<doc_id> - confirm delete one document
delx - cancel any delete
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .i18n import t


def welcome_keyboard(locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("button_english", locale), callback_data="lang:en")
    builder.button(text=t("button_russian", locale), callback_data="lang:ru")
    builder.button(text=t("button_settings", locale), callback_data="settings")
    builder.adjust(2, 1)
    return builder.as_markup()


def settings_keyboard(locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=_language_button("en", locale), callback_data="lang:en")
    builder.button(text=_language_button("ru", locale), callback_data="lang:ru")
    builder.button(text=t("button_delete_all", locale), callback_data="settings:reset")
    builder.button(text=t("button_close", locale), callback_data="settings:close")
    builder.adjust(2, 2)
    return builder.as_markup()


def reset_confirm_keyboard(locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("button_yes_delete", locale), callback_data="reset:yes")
    builder.button(text=t("button_cancel", locale), callback_data="reset:no")
    builder.adjust(2)
    return builder.as_markup()


def documents_keyboard(documents: list[dict], locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for document in documents:
        filename = _truncate_filename(str(document["filename"]))
        builder.button(
            text=t("button_delete_document", locale, filename=filename),
            callback_data=f"del:{document['id']}",
        )
    builder.adjust(*([1] * len(documents)))
    return builder.as_markup()


def delete_confirm_keyboard(doc_id: int, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("button_confirm", locale), callback_data=f"delc:{doc_id}")
    builder.button(text=t("button_cancel", locale), callback_data="delx")
    builder.adjust(2)
    return builder.as_markup()


def _language_button(language: str, locale: str) -> str:
    label = t("button_english" if language == "en" else "button_russian", locale)
    if language == locale:
        return f"· {label}"
    return label


def _truncate_filename(filename: str) -> str:
    if len(filename) <= 30:
        return filename
    return f"{filename[:29]}…"
