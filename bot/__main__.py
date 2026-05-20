import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from .config import settings
from .db import get_conn, init_schema
from .handlers import router


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("doc-assistant")


async def main():
    conn = get_conn()
    try:
        init_schema(conn)
    finally:
        conn.close()

    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start and choose language"),
            BotCommand(command="help", description="How uploads and cited answers work"),
            BotCommand(command="privacy", description="How document data is handled"),
            BotCommand(command="brief", description="Create an executive document brief"),
            BotCommand(command="faq", description="Create source-grounded Q&A"),
            BotCommand(command="quiz", description="Create an interactive quiz"),
            BotCommand(command="mindmap", description="Create a topic mind map"),
            BotCommand(command="list", description="View and delete documents"),
            BotCommand(command="settings", description="Language and account settings"),
            BotCommand(command="reset", description="Delete all your data"),
        ]
    )
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
