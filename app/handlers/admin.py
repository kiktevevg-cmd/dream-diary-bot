from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import crud
from app.db.models import async_session

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    async with async_session() as session:
        unprocessed = await crud.get_unprocessed_dreams(session, limit=10)
        total_dreams = len(unprocessed)

    await message.answer(
        f"🔧 <b>Admin panel</b>\n\n"
        f"Необработанных снов: {total_dreams}"
    )
