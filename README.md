# Doc-Assistant Bot

Telegram RAG assistant for PDF/DOCX/TXT. Upload a document, ask a question, get a cited answer.
Single-process Python with SQLite, sqlite-vec, fastembed (multilingual MiniLM) embeddings, and OpenRouter (DeepSeek V4 Flash) for answer generation.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Stack](https://img.shields.io/badge/stack-aiogram%20%7C%20OpenRouter%20%7C%20sqlite--vec-lightgrey)
![CI](https://github.com/kudnever/doc-assistant-bot/actions/workflows/ci.yml/badge.svg?branch=master)

**Live demo:** [@assistantdocumentbot](https://t.me/assistantdocumentbot) — may be offline when the maintainer's machine is off. Deploy your own in five minutes with the setup section below.

## Features

- PDF, DOCX, and TXT upload support
- OpenRouter (DeepSeek V4 Flash) answers with inline citations
- Bilingual EN/RU UI
- Inline-keyboard navigation
- Settings panel
- Clear `/privacy` disclosure for sensitive-document handling
- NotebookLM-style studio actions: overview, brief, FAQ, quiz, and mind map
- Per-document deletion
- Expandable source citations
- Multi-user isolation by Telegram `user_id`
- Vector search via sqlite-vec
- One-file SQLite database at `data/bot.db`
- Single-process Python app using aiogram long polling

## Architecture

```text
Telegram
   |
handlers
   |
parser -> chunker -> embeddings
   |                     |
   +---------------------v
              SQLite + sqlite-vec
                      |
                  OpenRouter
```

## Tech Stack

| Area | Choice |
| --- | --- |
| Runtime | Python 3.11+ |
| Telegram bot | aiogram 3.x long polling |
| LLM | OpenRouter (OpenAI-compatible) with DeepSeek V4 Flash |
| Embeddings | fastembed `BAAI/bge-small-en-v1.5`, 384 dimensions, local CPU |
| Vector storage | SQLite with sqlite-vec |
| PDF parsing | pypdf |
| DOCX parsing | python-docx |
| Config | pydantic-settings |

## Setup

```powershell
git clone <repo-url>
cd doc-assistant-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env with BOT_TOKEN and OPENROUTER_API_KEY.
python -m scripts.smoke
python -m bot
```

The first embedding run downloads the fastembed model (~90 MB) and caches it locally under the user's home cache directory.

On macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Telegram bot token from BotFather. |
| `OPENROUTER_API_KEY` | Yes | API key used for OpenRouter DeepSeek V4 Flash answers. |
| `MAX_CHUNKS_PER_DOC` | No | Maximum chunks per uploaded document after parsing and splitting. Defaults to `1200`. |

## Commands

| Command | Behavior |
| --- | --- |
| `/start` | Shows the short welcome message. |
| `/help` | Explains upload formats, size limit, and citations. |
| `/privacy` | Explains what is stored locally, what is sent to the LLM provider, and how deletion works. |
| `/brief` | Creates an executive summary for the latest uploaded document. |
| `/faq` | Creates source-grounded questions and answers for the latest uploaded document. |
| `/quiz` | Starts an interactive quiz for the latest uploaded document. |
| `/mindmap` | Creates a text topic map for the latest uploaded document. |
| `/list` | Lists your uploaded documents. |
| `/reset` | Deletes all documents and chunks for your Telegram user. |
| Send a file | Uploads and indexes a PDF, DOCX, or TXT file. |
| Ask a question | Answers from your uploaded documents with citations. |

## Project Structure

```text
doc-assistant-bot/
|-- bot/
|   |-- __init__.py
|   |-- __main__.py
|   |-- config.py
|   |-- db.py
|   |-- chunker.py
|   |-- parsers.py
|   |-- embeddings.py
|   |-- rag.py
|   |-- llm.py
|   `-- handlers.py
|-- scripts/
|   `-- smoke.py
|-- data/
|   `-- .gitkeep
|-- .env.example
|-- .gitignore
|-- requirements.txt
|-- README.md
`-- LICENSE
```

## Notable Implementation Details

- sqlite-vec extension loading happens on each new SQLite connection.
- Retrieval is filtered by Telegram `user_id`, so users only see their own documents.
- Uploaded files are downloaded to a temporary file, parsed, indexed, and then removed from temp storage.
- Chunking is character-based with overlap and soft paragraph/sentence breaks.
- Citation behavior is enforced through the OpenRouter answer prompt.
- Embeddings run locally on CPU via fastembed - no embedding API calls or keys needed.
- Answer generation sends the user's question and retrieved text chunks to the configured OpenRouter model.
- Bilingual UI with per-user locale persisted in SQLite; all strings centralised in bot/i18n.py.

## Telegram Profile Copy

Use this in BotFather so the bot's promise is clear before a user uploads a file.

**Short description**

```text
Ask questions about PDF, DOCX, and TXT files with cited answers. Local embeddings, per-user document isolation, and deletion controls.
```

**Description**

```text
Document Assistant reads PDF, DOCX, and TXT files and answers questions using cited passages from your documents.

Security model: documents are indexed for your Telegram account, embeddings run locally, and only the relevant text fragments plus your question are sent to the configured LLM provider for answer generation. Use /privacy for details, /list to delete one document, or /reset to delete all your data.
```

See [SECURITY.md](SECURITY.md) for the trust model and production hardening roadmap.

## Limitations / Roadmap

- No chat history
- No per-user quotas
- Blocking ingestion
- No admin panel
- OpenRouter free tier: 20 RPM / 50 RPD per free model; deposit $10+ once to unlock 1000 RPD
- Production migration path: Postgres+pgvector, Celery for ingestion, FastAPI webhook layer, Redis-backed rate-limit

## License

MIT
