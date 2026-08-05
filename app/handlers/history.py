from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import crud
from app.db.models import async_session
from app.keyboards.buttons import main_menu_keyboard

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
        await message.answer(
            "Пока нет записанных снов. Нажмите «Новый сон».",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines = ["📖 <b>Последние сны</b>\n"]
    for i, dream in enumerate(dreams, 1):
        date = dream.created_at.strftime("%d.%m.%Y")
        emotion = dream.emotional_focus or "—"
        text_preview = crud.decrypt_dream_text(dream)
        if len(text_preview) > 100:
            text_preview = text_preview[:100] + "..."

        interp = dream.interpretation or {}
        summary = dream.dialogue_summary or interp.get("closing_observation") or "—"
        if len(summary) > 180:
            summary = summary[:180] + "..."

        status = "диалог открыт" if dream.dialogue_status == "active" else "завершён"
        lines.append(
            f"<b>{i}.</b> {date} | 💭 {emotion} | {status}\n"
            f"<i>Сон:</i> {text_preview}\n"
            f"<i>Резюме:</i> {summary}\n"
        )

    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())
