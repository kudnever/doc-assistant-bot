# NotebookLM Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add NotebookLM-style text artifacts to the Telegram bot: upload overview, brief, FAQ, quiz, and mind map, without audio or video.

**Architecture:** Add a focused `bot/studio.py` module for prompt building, artifact generation, and quiz parsing/state. Extend `bot/rag.py` with safe per-user document chunk selection. Wire commands and inline buttons in `handlers.py` and `keyboards.py`.

**Tech Stack:** Python 3.11, aiogram, SQLite/sqlite-vec, OpenRouter-compatible chat completions, standard-library unittest.

---

### Task 1: Data Selection

**Files:**
- Modify: `bot/rag.py`
- Test: `tests/test_rag_documents.py`

- [x] Write failing unittest coverage for latest-document chunk selection, explicit document selection, and cross-user isolation.
- [x] Run `python -m unittest tests.test_rag_documents -v` and confirm missing function failure.
- [x] Implement `get_document_context(user_id, document_id=None, max_chunks=8)`.
- [x] Re-run the unittest target and confirm pass.

### Task 2: Studio Prompts and Quiz Parsing

**Files:**
- Create: `bot/studio.py`
- Test: `tests/test_studio.py`

- [x] Write failing tests for prompt labels, generated overview fallback, valid quiz JSON parsing, and invalid quiz rejection.
- [x] Run `python -m unittest tests.test_studio -v` and confirm missing module/function failures.
- [x] Implement prompt builders, `generate_artifact`, `generate_quiz`, and `QuizStore`.
- [x] Re-run the unittest target and confirm pass.

### Task 3: Telegram Wiring

**Files:**
- Modify: `bot/handlers.py`
- Modify: `bot/keyboards.py`
- Modify: `bot/i18n.py`
- Modify: `bot/__main__.py`
- Modify: `README.md`

- [x] Add studio keyboard buttons after upload.
- [x] Add `/brief`, `/faq`, `/quiz`, `/mindmap` command handlers.
- [x] Add `studio:<kind>:<doc_id>` callback handlers and quiz answer callbacks.
- [x] Add localized user-visible labels and empty/error messages.
- [x] Add BotFather command menu descriptions and README command docs.

### Task 4: Verification

**Files:**
- Test all changed Python modules.

- [x] Run `python -m unittest discover -v`.
- [x] Run `python -m compileall bot scripts tests`.
- [x] Run `python -m scripts.smoke`.
- [x] Review `git diff --check` and `git status --short`.
