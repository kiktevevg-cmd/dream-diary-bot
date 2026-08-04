from aiogram import Bot

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def setup_webhook(bot: Bot) -> None:
    if not settings.webhook_url:
        logger.warning("webhook_url_not_set", msg="Webhook URL is not configured, skipping setup")
        return

    webhook_url = f"{settings.webhook_url.rstrip('/')}{settings.webhook_path}"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret or None,
        drop_pending_updates=True,
    )
    logger.info("webhook_registered", url=webhook_url)


async def remove_webhook(bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("webhook_removed")
