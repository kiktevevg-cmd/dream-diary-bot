import io

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.db import crud
from app.db.models import async_session
from app.keyboards.buttons import format_interpretation, rating_keyboard
from app.services.dream_service import dream_service
from app.services.llm_service import LLMServiceError
from app.services.voice_service import VoiceServiceError, voice_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


class InterpretStates(StatesGroup):
    waiting_for_tag = State()
    waiting_for_insight = State()
    waiting_for_clarification = State()


async def _get_user(session, message: Message):
    return await crud.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )


async def _process_dream(message: Message, bot: Bot, dream_text: str, transcript: str | None = None) -> None:
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    async with async_session() as session:
        user = await _get_user(session, message)
        await session.commit()

        try:
            dream_id, interpretation = await dream_service.process_dream(
                session, user.id, dream_text, transcript
            )
            text = format_interpretation(interpretation)
            await message.answer(text, reply_markup=rating_keyboard(dream_id))

        except ValueError as e:
            await message.answer(f"⚠️ {e}")

        except LLMServiceError as e:
            logger.error("llm_unavailable", error=str(e))
            await message.answer(
                "😔 Не удалось получить интерпретацию от Kimi.\n"
                f"<code>{e}</code>\n\n"
                "Ваш сон сохранён — проверьте KIMI_API_KEY и LLM_MODEL на Railway, "
                "затем отправьте текст ещё раз."
            )


@router.message(Command("interpret"))
async def cmd_interpret(message: Message) -> None:
    await message.answer(
        "📝 Опишите ваш сон текстом или отправьте голосовое сообщение.\n"
        "Максимум 4000 символов."
    )


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot) -> None:
    if message.voice and message.voice.duration > 300:
        await message.answer("⚠️ Голосовое сообщение слишком длинное (макс. 5 минут).")
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    status_msg = await message.answer("🎤 Распознаю голосовое сообщение...")

    try:
        file = await bot.get_file(message.voice.file_id)
        file_bytes = io.BytesIO()
        await bot.download_file(file.file_path, file_bytes)
        transcript = await voice_service.transcribe(file_bytes.getvalue())
        await status_msg.edit_text(f"📝 <b>Расшифровка:</b>\n{transcript}")
        await _process_dream(message, bot, transcript, transcript=transcript)

    except VoiceServiceError as e:
        await status_msg.edit_text(f"⚠️ {e}")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_dream(message: Message, bot: Bot) -> None:
    if not message.text or len(message.text.strip()) < 10:
        await message.answer("⚠️ Опишите сон подробнее (минимум 10 символов).")
        return
    await _process_dream(message, bot, message.text.strip())


@router.callback_query(F.data.startswith("rate:"))
async def handle_rating(callback: CallbackQuery) -> None:
    _, dream_id_str, rating_str = callback.data.split(":")
    dream_id, rating = int(dream_id_str), int(rating_str)

    async with async_session() as session:
        user = await crud.get_or_create_user(
            session, telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )
        await session.commit()
        success = await dream_service.rate_dream(session, dream_id, user.id, rating)

    if success:
        await callback.answer(f"Спасибо! Оценка: {rating}/5 ⭐")
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.answer("Не удалось сохранить оценку", show_alert=True)


@router.callback_query(F.data.startswith("add_tag:"))
async def handle_add_tag(callback: CallbackQuery, state: FSMContext) -> None:
    dream_id = int(callback.data.split(":")[1])
    await state.set_state(InterpretStates.waiting_for_tag)
    await state.update_data(dream_id=dream_id)
    await callback.answer()
    await callback.message.answer("🏷 Введите ваш тег (одно слово или фраза):")


@router.message(InterpretStates.waiting_for_tag)
async def process_tag(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    dream_id = data["dream_id"]
    tag = message.text.strip()

    async with async_session() as session:
        user = await crud.get_or_create_user(
            session, telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await session.commit()
        success = await dream_service.add_user_tag(session, dream_id, user.id, tag)

    await state.clear()
    if success:
        await message.answer(f"✅ Тег «{tag}» добавлен.")
    else:
        await message.answer("⚠️ Не удалось добавить тег.")


@router.callback_query(F.data.startswith("insight:"))
async def handle_insight(callback: CallbackQuery, state: FSMContext) -> None:
    dream_id = int(callback.data.split(":")[1])
    await state.set_state(InterpretStates.waiting_for_insight)
    await state.update_data(dream_id=dream_id)
    await callback.answer()
    await callback.message.answer("💭 Запишите ваш инсайт или размышление о сне:")


@router.message(InterpretStates.waiting_for_insight)
async def process_insight(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    dream_id = data["dream_id"]

    async with async_session() as session:
        user = await crud.get_or_create_user(
            session, telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        await session.commit()
        success = await dream_service.save_insight(session, dream_id, user.id, message.text.strip())

    await state.clear()
    if success:
        await message.answer("✅ Инсайт сохранён.")
    else:
        await message.answer("⚠️ Не удалось сохранить инсайт.")


@router.callback_query(F.data.startswith("clarify:"))
async def handle_clarify(callback: CallbackQuery, state: FSMContext) -> None:
    dream_id = int(callback.data.split(":")[1])
    await state.set_state(InterpretStates.waiting_for_clarification)
    await state.update_data(dream_id=dream_id)
    await callback.answer()
    await callback.message.answer("❓ Задайте уточняющий вопрос по интерпретации:")


@router.message(InterpretStates.waiting_for_clarification)
async def process_clarification(message: Message, bot: Bot, state: FSMContext) -> None:
    data = await state.get_data()
    dream_id = data["dream_id"]

    async with async_session() as session:
        user = await crud.get_or_create_user(
            session, telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        dream = await crud.get_dream_by_id(session, dream_id, user.id)
        if not dream or not dream.interpretation:
            await state.clear()
            await message.answer("⚠️ Сон не найден.")
            return

        dream_text = crud.decrypt_dream_text(dream)
        question = message.text.strip()
        combined = (
            f"Контекст сна: {dream_text}\n\n"
            f"Предыдущая интерпретация: {dream.interpretation.get('interpretation', '')}\n\n"
            f"Уточняющий вопрос пользователя: {question}"
        )

    await state.clear()
    await _process_dream(message, bot, combined)
