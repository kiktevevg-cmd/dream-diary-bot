import io

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.db import crud
from app.db.models import async_session
from app.keyboards.buttons import (
    BTN_FINISH,
    BTN_HISTORY,
    BTN_INSIGHT,
    BTN_MY_INSIGHTS,
    BTN_NEW_DREAM,
    BTN_SKIP,
    MENU_BUTTONS,
    format_interpretation,
    main_menu_keyboard,
    split_telegram_message,
)
from app.services.dream_service import dream_service
from app.services.llm_service import LLMServiceError
from app.services.voice_service import VoiceServiceError, voice_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


class DialogueStates(StatesGroup):
    waiting_for_dream = State()
    waiting_for_insight = State()


async def _get_user(session, message: Message):
    return await crud.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )


async def _send_parts(message: Message, text: str) -> None:
    for part in split_telegram_message(text):
        await message.answer(part, reply_markup=main_menu_keyboard())


async def _process_dream(
    message: Message,
    bot: Bot,
    state: FSMContext,
    dream_text: str,
    transcript: str | None = None,
) -> None:
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    async with async_session() as session:
        user = await _get_user(session, message)
        await session.commit()

        try:
            _, interpretation = await dream_service.process_dream(
                session, user.id, dream_text, transcript
            )
            await state.clear()
            await _send_parts(message, format_interpretation(interpretation))

        except ValueError as e:
            await message.answer(f"⚠️ {e}", reply_markup=main_menu_keyboard())

        except LLMServiceError as e:
            logger.error("llm_unavailable", error=str(e))
            await message.answer(
                "Не удалось получить интерпретацию.\n"
                f"<code>{e}</code>\n\n"
                "Сон сохранён. Попробуйте ещё раз чуть позже или нажмите «Новый сон».",
                reply_markup=main_menu_keyboard(),
            )


@router.message(Command("interpret"))
async def cmd_interpret(message: Message, state: FSMContext) -> None:
    await state.set_state(DialogueStates.waiting_for_dream)
    await message.answer(
        "Опишите сон текстом или голосовым сообщением (до 4000 символов).",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == BTN_NEW_DREAM)
async def btn_new_dream(message: Message, state: FSMContext) -> None:
    async with async_session() as session:
        user = await _get_user(session, message)
        await dream_service.start_new_dream(session, user.id)
    await state.set_state(DialogueStates.waiting_for_dream)
    await message.answer(
        "Готов к новому сну. Опишите его текстом или голосом.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == BTN_SKIP)
async def btn_skip(message: Message, bot: Bot, state: FSMContext) -> None:
    await state.clear()
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    async with async_session() as session:
        user = await _get_user(session, message)
        try:
            reply = await dream_service.continue_dialogue(
                session,
                user.id,
                "Хочу пропустить текущий вопрос и перейти дальше.",
                skip_question=True,
            )
            await _send_parts(message, reply)
        except ValueError as e:
            await message.answer(str(e), reply_markup=main_menu_keyboard())
        except LLMServiceError as e:
            await message.answer(f"Не удалось продолжить диалог: <code>{e}</code>", reply_markup=main_menu_keyboard())


@router.message(F.text == BTN_FINISH)
async def btn_finish(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        user = await _get_user(session, message)
        text = await dream_service.finish_dialogue(session, user.id)
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(F.text == BTN_INSIGHT)
async def btn_insight(message: Message, state: FSMContext) -> None:
    await state.set_state(DialogueStates.waiting_for_insight)
    await message.answer(
        "Запишите свой инсайт — мысль, вывод или ощущение, которое хотите сохранить.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(DialogueStates.waiting_for_insight, F.text)
async def process_insight(message: Message, state: FSMContext) -> None:
    if not message.text or message.text in MENU_BUTTONS:
        return
    async with async_session() as session:
        user = await _get_user(session, message)
        await dream_service.save_insight(session, user.id, message.text.strip())
    await state.clear()
    await message.answer(
        "Инсайт сохранён. Посмотреть все можно в «Мои инсайты».",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == BTN_MY_INSIGHTS)
@router.message(Command("my_insights"))
async def btn_my_insights(message: Message) -> None:
    async with async_session() as session:
        user = await _get_user(session, message)
        insights = await crud.get_user_insights(session, user.id, limit=15)

    if not insights:
        await message.answer(
            "Пока нет сохранённых инсайтов. Во время разбора нажмите «Инсайт».",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines = ["💡 <b>Ваши инсайты</b>\n"]
    for i, item in enumerate(insights, 1):
        date = item.created_at.strftime("%d.%m.%Y")
        preview = item.text[:200] + ("..." if len(item.text) > 200 else "")
        lines.append(f"<b>{i}.</b> {date}\n{preview}\n")
    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


@router.message(F.text == BTN_HISTORY)
async def btn_history(message: Message) -> None:
    from app.handlers.history import cmd_history

    await cmd_history(message)


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot, state: FSMContext) -> None:
    if message.voice and message.voice.duration > 300:
        await message.answer("Голосовое слишком длинное (макс. 5 минут).", reply_markup=main_menu_keyboard())
        return

    current = await state.get_state()
    async with async_session() as session:
        user = await _get_user(session, message)
        active = await crud.get_active_dream(session, user.id)
        has_active = active is not None

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    status_msg = await message.answer("Распознаю голосовое сообщение...")

    try:
        file = await bot.get_file(message.voice.file_id)
        file_bytes = io.BytesIO()
        await bot.download_file(file.file_path, file_bytes)
        transcript = await voice_service.transcribe(file_bytes.getvalue())
        await status_msg.edit_text(f"<b>Расшифровка:</b>\n{transcript}")

        if has_active and current != DialogueStates.waiting_for_dream.state:
            async with async_session() as session:
                user = await _get_user(session, message)
                reply = await dream_service.continue_dialogue(session, user.id, transcript)
            await _send_parts(message, reply)
        else:
            await _process_dream(message, bot, state, transcript, transcript=transcript)

    except VoiceServiceError as e:
        await status_msg.edit_text(f"⚠️ {e}")
    except LLMServiceError as e:
        await message.answer(
            f"Не удалось продолжить диалог: <code>{e}</code>",
            reply_markup=main_menu_keyboard(),
        )
    except ValueError as e:
        await message.answer(str(e), reply_markup=main_menu_keyboard())


@router.message(DialogueStates.waiting_for_dream, F.text)
async def handle_new_dream_text(message: Message, bot: Bot, state: FSMContext) -> None:
    if not message.text or message.text in MENU_BUTTONS:
        return
    if len(message.text.strip()) < 10:
        await message.answer("Опишите сон подробнее (минимум 10 символов).", reply_markup=main_menu_keyboard())
        return
    await _process_dream(message, bot, state, message.text.strip())


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, bot: Bot, state: FSMContext) -> None:
    if not message.text or message.text in MENU_BUTTONS:
        return

    text = message.text.strip()
    async with async_session() as session:
        user = await _get_user(session, message)
        active = await crud.get_active_dream(session, user.id)

    if active:
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        async with async_session() as session:
            user = await _get_user(session, message)
            try:
                reply = await dream_service.continue_dialogue(session, user.id, text)
                await _send_parts(message, reply)
            except ValueError as e:
                await message.answer(str(e), reply_markup=main_menu_keyboard())
            except LLMServiceError as e:
                await message.answer(
                    f"Не удалось продолжить диалог: <code>{e}</code>",
                    reply_markup=main_menu_keyboard(),
                )
        return

    if len(text) < 10:
        await message.answer(
            "Опишите сон подробнее (минимум 10 символов) или нажмите «Новый сон».",
            reply_markup=main_menu_keyboard(),
        )
        return

    await _process_dream(message, bot, state, text)
