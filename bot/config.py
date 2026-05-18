from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    anthropic_api_key: str
    voyage_api_key: str = ""
    db_path: str = "data/bot.db"
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 5
    max_file_mb: int = 20
    answer_model: str = "claude-haiku-4-5-20251001"


settings = Settings()
