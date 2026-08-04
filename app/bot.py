from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.core.config import settings
from app.handlers import admin, history, insights, interpret, settings as settings_handler, start, stats

storage = RedisStorage.from_url(settings.redis_url)

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=storage)

dp.include_router(start.router)
dp.include_router(interpret.router)
dp.include_router(history.router)
dp.include_router(stats.router)
dp.include_router(insights.router)
dp.include_router(settings_handler.router)
dp.include_router(admin.router)
