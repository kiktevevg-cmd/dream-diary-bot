from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, Message

from app.keyboards.buttons import main_menu_keyboard

router = Router()

WELCOME_TEXT = (
    "🌙 <b>Дневник снов</b>\n\n"
    "Сны — это язык вашего бессознательного. Мы не гадаем, мы анализируем.\n\n"
    "Опишите сон — получите психологический разбор и сможете продолжить диалог "
    "для самоанализа.\n\n"
    "Кнопки меню:\n"
    "• <b>Новый сон</b> — начать новый разбор\n"
    "• <b>Инсайт</b> — сохранить мысль\n"
    "• <b>Мои инсайты</b> — ваши сохранённые выводы\n"
    "• <b>Пропустить</b> — перейти к другому вопросу\n"
    "• <b>Завершить разбор</b> — закрыть текущий диалог\n"
    "• <b>История</b> — прошлые сны и обсуждения"
)

HELP_TEXT = (
    "📚 <b>Справка</b>\n\n"
    "<b>Меню:</b> Новый сон, Инсайт, Мои инсайты, Пропустить, Завершить разбор, История\n\n"
    "<b>Команды:</b>\n"
    "/start — приветствие и меню\n"
    "/history — история снов\n"
    "/my_insights — сохранённые инсайты\n"
    "/stats — динамика эмоций\n"
    "/insights — паттерны образов\n"
    "/settings — настройки\n"
    "/clear — удалить историю снов\n"
    "/delete_my_data — полное удаление данных\n\n"
    "Подход: научная психология, без эзотерики и предсказаний."
)

BOT_COMMANDS = [
    BotCommand(command="start", description="Приветствие и меню"),
    BotCommand(command="history", description="История снов"),
    BotCommand(command="my_insights", description="Мои инсайты"),
    BotCommand(command="stats", description="Статистика эмоций"),
    BotCommand(command="insights", description="Паттерны образов"),
    BotCommand(command="help", description="Справка"),
    BotCommand(command="settings", description="Настройки"),
]


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())
