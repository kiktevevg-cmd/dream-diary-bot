from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.validators import DreamInterpretation

TELEGRAM_MESSAGE_LIMIT = 3900


def rating_keyboard(dream_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=str(i), callback_data=f"rate:{dream_id}:{i}")
        for i in range(1, 6)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [
            InlineKeyboardButton(text="🏷 Добавить тег", callback_data=f"add_tag:{dream_id}"),
            InlineKeyboardButton(text="💭 Инсайт", callback_data=f"insight:{dream_id}"),
        ],
        [
            InlineKeyboardButton(text="❓ Уточнить", callback_data=f"clarify:{dream_id}"),
        ],
    ])


def format_interpretation(interpretation: DreamInterpretation) -> str:
    images_block = []
    for item in interpretation.key_images_analysis:
        images_block.append(f"<b>{item.image}</b>\n{item.analysis}")

    triggers_block = []
    for i, trigger in enumerate(interpretation.potential_triggers, 1):
        triggers_block.append(f"<b>{i}. {trigger.title}</b>\n{trigger.description}")

    questions = "\n".join(f"• {q}" for q in interpretation.self_analysis_questions)
    tags = " ".join(f"#{t}" for t in interpretation.tags)

    return (
        f"{interpretation.intro}\n\n"
        f"<b>Что может стоять за ключевыми образами</b>\n\n"
        f"{chr(10).join(images_block)}\n\n"
        f"💭 <b>Эмоциональный фон:</b> {interpretation.emotional_focus}\n\n"
        f"<b>Возможные психологические триггеры</b>\n\n"
        f"{chr(10).join(triggers_block)}\n\n"
        f"<b>Вопросы для вашего самоанализа</b>\n\n"
        f"{questions}\n\n"
        f"<b>Наблюдение для размышления</b>\n\n"
        f"{interpretation.closing_observation}\n\n"
        f"<i>{interpretation.reflection_question}</i>\n\n"
        f"🏷 {tags}"
    )


def split_telegram_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
        if len(block) <= limit:
            current = block
        else:
            for i in range(0, len(block), limit):
                parts.append(block[i : i + limit])
            current = ""
    if current:
        parts.append(current)
    return parts or [text[:limit]]


def confirm_delete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete"),
        ],
    ])
