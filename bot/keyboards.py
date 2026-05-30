"""Inline keyboard factories.

Callback data prefixes:
lang:<locale>     - set locale (en, ru, es, de, fr, zh, pt)
settings          - open settings panel
settings:close    - close settings
settings:reset    - open reset confirm
reset:yes / reset:no - confirm/cancel full reset
del:<doc_id>      - open per-document delete confirm
delc:<doc_id>     - confirm delete one document
delx              - cancel any delete
studio:<kind>:<doc_id> - generate a NotebookLM-style artifact
quiz:<token>:<qidx>:<answer_idx> - answer a quiz question
quiznext:<token>:<qidx> - move to the next quiz question
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .i18n import t


# Native-name button key per locale. Used by both the welcome row and the
# settings language grid.
_LANGUAGE_BUTTONS = {
    "en": "button_english",
    "ru": "button_russian",
    "es": "button_spanish",
    "de": "button_german",
    "fr": "button_french",
    "zh": "button_chinese",
    "pt": "button_portuguese",
}

# Display order for the language picker. EN/RU first as the most common pair,
# then the remaining five in alphabetical order of their two-letter code.
_LANGUAGE_ORDER = ("en", "ru", "es", "de", "fr", "zh", "pt")


def welcome_keyboard(locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code in _LANGUAGE_ORDER:
        builder.button(
            text=t(_LANGUAGE_BUTTONS[code], locale),
            callback_data=f"lang:{code}",
        )
    builder.button(text=t("button_settings", locale), callback_data="settings")
    # 7 language buttons in a 2-column grid + Settings on its own row
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()


def studio_keyboard(doc_id: int, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for kind, key in (
        ("brief", "button_brief"),
        ("faq", "button_faq"),
        ("quiz", "button_quiz"),
        ("mindmap", "button_mindmap"),
    ):
        builder.button(text=t(key, locale), callback_data=f"studio:{kind}:{doc_id}")
    builder.button(text=t("button_privacy", locale), callback_data=f"studio:privacy:{doc_id}")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def settings_keyboard(locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code in _LANGUAGE_ORDER:
        builder.button(
            text=_language_button(code, locale),
            callback_data=f"lang:{code}",
        )
    builder.button(text=t("button_delete_all", locale), callback_data="settings:reset")
    builder.button(text=t("button_close", locale), callback_data="settings:close")
    # 7 language buttons (2-column grid, last row has 1) + 2 action buttons
    builder.adjust(2, 2, 2, 1, 2)
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
        doc_id = document["id"]
        filename = _truncate_filename(str(document["filename"]))
        for kind, key in (
            ("brief", "button_brief"),
            ("faq", "button_faq"),
            ("quiz", "button_quiz"),
            ("mindmap", "button_mindmap"),
        ):
            builder.button(text=t(key, locale), callback_data=f"studio:{kind}:{doc_id}")
        builder.button(
            text=t("button_delete_document", locale, filename=filename),
            callback_data=f"del:{doc_id}",
        )
    builder.adjust(*([3, 2] * len(documents)))
    return builder.as_markup()


def delete_confirm_keyboard(doc_id: int, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("button_confirm", locale), callback_data=f"delc:{doc_id}")
    builder.button(text=t("button_cancel", locale), callback_data="delx")
    builder.adjust(2)
    return builder.as_markup()


def quiz_question_keyboard(
    token: str, question_index: int, options: list[str]
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, option in enumerate(options):
        builder.button(
            text=f"{chr(65 + idx)}. {_truncate_option(option)}",
            callback_data=f"quiz:{token}:{question_index}:{idx}",
        )
    builder.adjust(1)
    return builder.as_markup()


def quiz_next_keyboard(token: str, question_index: int, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("button_next_question", locale),
        callback_data=f"quiznext:{token}:{question_index}",
    )
    return builder.as_markup()


def _language_button(language: str, locale: str) -> str:
    """Render the language button label, marking it active when it matches."""
    label = t(_LANGUAGE_BUTTONS[language], locale)
    if language == locale:
        return f"· {label}"
    return label


def _truncate_filename(filename: str) -> str:
    if len(filename) <= 30:
        return filename
    return f"{filename[:29]}…"


def _truncate_option(option: str) -> str:
    if len(option) <= 38:
        return option
    return f"{option[:37]}…"
