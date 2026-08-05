from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.utils.validators import DreamInterpretation

TELEGRAM_MESSAGE_LIMIT = 3900

BTN_NEW_DREAM = "Новый сон"
BTN_INSIGHT = "Инсайт"
BTN_MY_INSIGHTS = "Мои инсайты"
BTN_SKIP = "Пропустить"
BTN_FINISH = "Завершить разбор"
BTN_HISTORY = "История"

MENU_BUTTONS = {
    BTN_NEW_DREAM,
    BTN_INSIGHT,
    BTN_MY_INSIGHTS,
    BTN_SKIP,
    BTN_FINISH,
    BTN_HISTORY,
    "✅ Да, удалить",
    "❌ Отмена",
}


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_DREAM), KeyboardButton(text=BTN_INSIGHT)],
            [KeyboardButton(text=BTN_SKIP), KeyboardButton(text=BTN_FINISH)],
            [KeyboardButton(text=BTN_MY_INSIGHTS), KeyboardButton(text=BTN_HISTORY)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def format_interpretation(interpretation: DreamInterpretation) -> str:
    images_block = []
    for item in interpretation.key_images_analysis:
        images_block.append(f"<b>{item.image}</b>\n{item.analysis}")

    triggers_block = []
    for i, trigger in enumerate(interpretation.potential_triggers, 1):
        triggers_block.append(f"<b>{i}. {trigger.title}</b>\n{trigger.description}")

    tags = " ".join(f"#{t}" for t in interpretation.tags)
    framing = interpretation.intro.strip() if interpretation.intro else ""

    parts = [
        "Спасибо, что поделились этим сном.",
    ]
    if framing and "спасибо" not in framing.lower() and "доверие" not in framing.lower():
        parts.append(framing)

    parts.extend([
        "",
        "<b>Что может стоять за ключевыми образами</b>",
        "",
        "\n\n".join(images_block),
        "",
        f"💭 <b>Эмоциональный фон:</b> {interpretation.emotional_focus}",
        "",
        "<b>Возможные психологические триггеры</b>",
        "",
        "\n\n".join(triggers_block),
        "",
        "<b>Резюме</b>",
        "",
        interpretation.closing_observation,
        "",
        "<b>Вопрос для самоанализа</b>",
        "",
        interpretation.reflection_question,
        "",
        "Вы можете продолжить обсуждение, если у вас возникли вопросы по интерпретации "
        "или появились новые мысли. Напишите ответ на вопрос или свой вопрос — разберём вместе.",
        "",
        f"🏷 {tags}" if tags else "",
    ])
    return "\n".join(p for p in parts if p is not None).strip()


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


def confirm_delete_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да, удалить"), KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
