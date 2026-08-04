"""Polling mode for local development (no webhook/SSL required)."""

import asyncio
import logging

from app.bot import bot, dp
from app.db.models import close_db, init_db
from app.db.redis_client import close_redis
from app.utils.logger import setup_logging

setup_logging()
logging.getLogger("aiogram").setLevel(logging.INFO)


async def main() -> None:
    await init_db()
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await close_db()
        await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
