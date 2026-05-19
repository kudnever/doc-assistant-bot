import asyncio
import logging

from aiogram import Bot, Dispatcher

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

    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
