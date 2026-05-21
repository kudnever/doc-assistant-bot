from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    openrouter_api_key: str

    db_path: str = "data/bot.db"
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 5
    max_file_mb: int = 20

    # Resource caps to defend against pathological uploads
    max_chunks_per_doc: int = 1200         # caps chunk count after splitting
    max_docs_per_user: int = 20            # storage cap per Telegram user_id
    max_uncompressed_mb: int = 100         # ZIP-bomb guard for DOCX archives

    # OpenRouter / model config
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    answer_model: str = "deepseek/deepseek-v4-flash:free"
    answer_max_tokens: int = 1024
    # Greedy chunk packing budget for the answer prompt's context block.
    # Excludes the question and template overhead — those are accounted for
    # separately. Tuned for free-tier models with ~32k windows.
    answer_context_budget_tokens: int = 6000

    # Embeddings — multilingual model supporting 50+ languages (EN/RU/DE/etc.)
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    # Optional OpenRouter ranking headers
    app_url: str = "https://github.com/kudnever/doc-assistant-bot"
    app_title: str = "doc-assistant-bot"


settings = Settings()
