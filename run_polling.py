"""Polling mode for local development."""

import asyncio

from app.bot import bot, dp
from app.db.models import close_db, init_db
from app.db.redis_client import close_redis
from app.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


async def main() -> None:
    logger.info("starting_polling_mode")
    await init_db()
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await close_db()
        await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
