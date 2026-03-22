import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import BotCommand
from aiogram.filters import Command

from config import settings
from db import create_db
from commands import (done_command, start_command, setgoal_command, stats_command, reset_command,
                      process_photo_and_additional, eat_command, add_meal_callback,
                      show_stats_callback, reset_stats_callback)

# Инициализируем бота и диспетчер
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Логирование
logging.basicConfig(level=logging.INFO)

dp.message.register(start_command, Command("start"))
dp.message.register(setgoal_command, Command("setgoal"))
dp.message.register(stats_command, Command("stats"))
dp.message.register(reset_command, Command("reset"))
dp.message.register(done_command, Command("done"))
dp.message.register(process_photo_and_additional, F.photo)
dp.message.register(eat_command, Command("eat"))
dp.callback_query.register(show_stats_callback, F.data == "show_stats")
dp.callback_query.register(add_meal_callback, F.data == "add_meal")
dp.callback_query.register(reset_stats_callback, F.data == "reset_stats")


async def main():
    """Запуск бота."""
    await create_db()
    await bot.set_my_commands(commands=[
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="stats", description="Показать статистику за день"),
        BotCommand(command="setgoal", description="Установить дневную норму калорий (/setgoal 2000)"),
        BotCommand(command="reset", description="Сбросить статистику за день"),
    ])

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
