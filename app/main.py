from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app.api.routes import router as api_router
from app.bot import bot, dp
from app.core.config import settings
from app.core.webhook import remove_webhook, setup_webhook
from app.db.models import close_db, init_db
from app.db.redis_client import close_redis
from app.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", environment=settings.environment)
    await init_db()
    if settings.webhook_url:
        await setup_webhook(bot)
    yield
    if settings.webhook_url:
        await remove_webhook(bot)
    await bot.session.close()
    await close_db()
    await close_redis()
    logger.info("app_shutdown")


app = FastAPI(title="Dream Diary Bot", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dream-diary-bot"}


@app.post(settings.webhook_path)
async def webhook_handler(request: Request) -> Response:
    if settings.webhook_secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if token != settings.webhook_secret:
            return Response(status_code=403)

    update = await request.json()
    await dp.feed_webhook_update(bot, update)
    return Response(status_code=200)
