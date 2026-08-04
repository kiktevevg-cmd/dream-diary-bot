from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.validators import DreamInterpretation


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
    images = ", ".join(interpretation.key_images)
    triggers = ", ".join(interpretation.potential_triggers)
    tags = " ".join(f"#{t}" for t in interpretation.tags)

    return (
        f"🌙 <b>Анализ сна</b>\n\n"
        f"🔑 <b>Ключевые образы:</b> {images}\n"
        f"💭 <b>Эмоциональный фон:</b> {interpretation.emotional_focus}\n\n"
        f"📖 <b>Интерпретация:</b>\n{interpretation.interpretation}\n\n"
        f"🔗 <b>Возможные триггеры:</b> {triggers}\n\n"
        f"❓ <b>Ассоциация:</b> {interpretation.associations_question}\n\n"
        f"🤔 <b>Для размышления:</b> {interpretation.reflection_question}\n\n"
        f"🏷 {tags}"
    )


def confirm_delete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete"),
        ],
    ])
