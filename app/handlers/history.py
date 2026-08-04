from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import crud
from app.db.models import async_session

router = Router()


@router.message(Command("history"))
async def cmd_history(message: Message) -> None:
    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        dreams = await crud.get_user_dreams(session, user.id, limit=10)

    if not dreams:
        await message.answer("📭 У вас пока нет записанных снов. Опишите свой первый сон!")
        return

    lines = ["📖 <b>Последние сны</b>\n"]
    for i, dream in enumerate(dreams, 1):
        date = dream.created_at.strftime("%d.%m.%Y")
        emotion = dream.emotional_focus or "—"
        tags = " ".join(f"#{t}" for t in (dream.tags or []))
        text_preview = crud.decrypt_dream_text(dream)[:80]
        if len(crud.decrypt_dream_text(dream)) > 80:
            text_preview += "..."
        lines.append(
            f"<b>{i}.</b> {date} | 💭 {emotion}\n"
            f"   {text_preview}\n"
            f"   {tags}\n"
        )

    await message.answer("\n".join(lines))
