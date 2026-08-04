from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router()

WELCOME_TEXT = (
    "🌙 <b>Дневник снов</b>\n\n"
    "Сны — это язык вашего бессознательного. Мы не гадаем, мы анализируем.\n\n"
    "Системный подход к интерпретации сновидений, основанный на проверенных "
    "психологических школах: КПТ, аналитическая психология, нейробиология сна, "
    "гештальт-терапия, экзистенциальная психология.\n\n"
    "📝 Просто отправьте текст или голосовое сообщение с описанием сна — "
    "и получите психологический анализ.\n\n"
    "Используйте /help для списка команд."
)

HELP_TEXT = (
    "📚 <b>Справка — Дневник снов</b>\n\n"
    "<b>Команды:</b>\n"
    "/start — приветствие\n"
    "/interpret — интерпретация сна\n"
    "/history — последние 10 снов\n"
    "/stats — динамика эмоций и теги\n"
    "/insights — паттерны и повторяющиеся образы\n"
    "/settings — настройки\n"
    "/clear — удалить историю снов\n"
    "/delete_my_data — полное удаление данных\n\n"
    "<b>Наш подход:</b>\n"
    "Мы используем научные методы психологии для анализа снов. "
    "Никакой эзотерики, мистики или предсказаний — только инструменты "
    "для вашего самоанализа и понимания себя.\n\n"
    "Просто отправьте текст сна (до 4000 символов) или голосовое сообщение."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
