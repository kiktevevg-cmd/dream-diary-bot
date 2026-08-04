from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import crud
from app.db.models import async_session
from app.services.analytics_service import analytics_service

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        emotions = await analytics_service.get_emotional_dynamics(session, user.id)
        tags = await analytics_service.get_tag_frequency(session, user.id)

    await message.answer(emotions + tags)
