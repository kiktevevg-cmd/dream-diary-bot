import asyncio
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

STARTUP_TIMEOUT_SEC = 20


async def _startup() -> None:
    try:
        await asyncio.wait_for(init_db(), timeout=STARTUP_TIMEOUT_SEC)
        logger.info("db_initialized")
    except TimeoutError:
        logger.error("db_init_timeout", hint="Check DATABASE_URL and PostgreSQL plugin on Railway")
    except Exception as e:
        logger.error("db_init_failed", error=str(e), hint="Add PostgreSQL plugin on Railway")

    if settings.webhook_url:
        try:
            await setup_webhook(bot)
        except Exception as e:
            logger.error("webhook_setup_failed", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", environment=settings.environment)
    startup_task = asyncio.create_task(_startup())
    yield
    if not startup_task.done():
        startup_task.cancel()
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
