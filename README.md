# Doc-Assistant Bot

Doc-Assistant Bot - Telegram RAG assistant for PDF/DOCX. Upload -> ask -> get cited answers.
Single-process Python MVP using SQLite, sqlite-vec, fastembed (BGE small) embeddings, and OpenRouter (DeepSeek V4 Flash) answers.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Stack](https://img.shields.io/badge/stack-aiogram%20%7C%20OpenRouter%20%7C%20sqlite--vec-lightgrey)

## Demo

![Demo](docs/demo.gif)

## Features

- PDF, DOCX, and TXT upload support
- OpenRouter (DeepSeek V4 Flash) answers with inline citations
- Bilingual EN/RU UI
- Inline-keyboard navigation
- Settings panel
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

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Telegram bot token from BotFather. |
| `OPENROUTER_API_KEY` | Yes | API key used for OpenRouter DeepSeek V4 Flash answers. |

## Commands

| Command | Behavior |
| --- | --- |
| `/start` | Shows the short welcome message. |
| `/help` | Explains upload formats, size limit, and citations. |
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
- Chunking is character-based with overlap and soft paragraph/sentence breaks.
- Citation behavior is enforced through the OpenRouter answer prompt.
- Embeddings run locally on CPU via fastembed - no embedding API calls or keys needed; only the LLM provider key is required to run the bot.
- Bilingual UI with per-user locale persisted in SQLite; all strings centralised in bot/i18n.py.

## Limitations / Roadmap

- No chat history
- No per-user quotas
- Blocking ingestion
- No admin panel
- OpenRouter free tier: 20 RPM / 50 RPD per free model; deposit $10+ once to unlock 1000 RPD
- Production migration path: Postgres+pgvector, Celery for ingestion, FastAPI webhook layer, Redis-backed rate-limit

## License

MIT
