from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import crud
from app.db.models import async_session
from app.db.redis_client import invalidate_dream_cache
from app.keyboards.buttons import confirm_delete_keyboard, main_menu_keyboard

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        settings = user.settings or {}

    lang = settings.get("language", "ru")
    reminders = "включены" if settings.get("reminders", False) else "выключены"

    await message.answer(
        f"⚙️ <b>Настройки</b>\n\n"
        f"🌐 Язык: {lang}\n"
        f"🔔 Напоминания: {reminders}\n\n"
        f"Для удаления данных: /clear или /delete_my_data",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    await message.answer(
        "Вы уверены, что хотите удалить всю историю снов?\n"
        "Это действие необратимо.",
        reply_markup=confirm_delete_keyboard(),
    )


@router.message(F.text == "✅ Да, удалить")
async def confirm_clear(message: Message) -> None:
    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        count = await crud.clear_user_history(session, user.id)
        await session.commit()
        await invalidate_dream_cache(user.id)

    await message.answer(f"Удалено снов: {count}", reply_markup=main_menu_keyboard())


@router.message(F.text == "❌ Отмена")
async def cancel_clear(message: Message) -> None:
    await message.answer("Удаление отменено.", reply_markup=main_menu_keyboard())


@router.message(Command("delete_my_data"))
async def cmd_delete_data(message: Message) -> None:
    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await crud.delete_user_data(session, user.id)
        await session.commit()

    await message.answer(
        "Все ваши данные полностью удалены.\n"
        "Чтобы вернуться — отправьте /start.",
        reply_markup=main_menu_keyboard(),
    )
