import os

# bot.config.settings is initialized at import time and requires these env vars.
os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
