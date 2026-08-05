from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import crud
from app.db.models import async_session
from app.keyboards.buttons import main_menu_keyboard
from app.services.analytics_service import analytics_service

router = Router()


@router.message(Command("insights"))
async def cmd_insights(message: Message) -> None:
    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        patterns = await analytics_service.get_insights(session, user.id)
        notes = await crud.get_user_insights(session, user.id, limit=5)

    lines = [patterns, ""]
    if notes:
        lines.append("💡 <b>Последние сохранённые инсайты</b>")
        for item in notes:
            date = item.created_at.strftime("%d.%m.%Y")
            preview = item.text[:150] + ("..." if len(item.text) > 150 else "")
            lines.append(f"• {date}: {preview}")
        lines.append("\nВсе инсайты: кнопка «Мои инсайты» или /my_insights")
    else:
        lines.append("Сохранённых инсайтов пока нет — используйте кнопку «Инсайт».")

    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())
