import logging
import base64
import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BotCommand
from aiogram.filters import Command
from dotenv import load_dotenv
from openai import OpenAI
from db import (create_db, add_meal, get_meals_for_today, get_daily_calories,
                get_calories_consumed, reset_daily_meals, set_daily_goal)

# Загружаем переменные окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Инициализируем бота и диспетчер
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Инициализируем OpenAI API
client = OpenAI(api_key=OPENAI_API_KEY)

# Логирование
logging.basicConfig(level=logging.INFO)

# Глобальный словарь для хранения последнего распознанного блюда
last_meals = {}


@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Привет! Отправь фото блюда с подписью, начинающейся с /calc.")


@dp.message(Command("setgoal"))
async def setgoal_command(message: types.Message):
    args = message.text.split()[1:]
    if not args or not args[0].isdigit():
        await message.answer("⚠ Укажите число, например: /setgoal 1800")
        return
    await set_daily_goal(message.from_user.id, int(args[0]))
    await message.answer(f"🎯 Ваша новая цель: {args[0]} ккал в день!")


@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    user_id = message.from_user.id
    consumed = await get_calories_consumed(user_id)
    daily = await get_daily_calories(user_id)
    remaining = daily - consumed
    meals = await get_meals_for_today(user_id)
    meals_text = "\n".join([f"🍽 {name} — {calories} ккал" for name, calories in meals]) if meals else "📭 Нет записей"
    await message.answer(
        f"📊 *Статистика на сегодня:*\n✅ Съедено: {consumed} ккал\n🔻 Осталось: {remaining} ккал\n\n🍽 Съеденные блюда:\n{meals_text}",
        parse_mode="Markdown"
    )


@dp.message(Command("reset"))
async def reset_command(message: types.Message):
    await reset_daily_meals(message.from_user.id)
    await message.answer("📭 Ваша статистика за сегодня обнулена!")


@dp.message(Command("done"))
async def done_command(message: types.Message):
    user_id = message.from_user.id

    if user_id not in last_meals:
        await message.answer("⚠ Нет сохранённого блюда. Сначала отправьте фото с /calc.")
        return

    meal = last_meals[user_id]
    await add_meal(user_id, meal["название"], meal["калории"])
    del last_meals[user_id]

    consumed = await get_calories_consumed(user_id)
    remaining = (await get_daily_calories(user_id)) - consumed

    meal_text = (
        f"✅ *Блюдо добавлено в дневник!*\n\n"
        f"🍽 *Название*: {meal['название']}\n"
        f"🔥 *Калории*: {meal['калории']} ккал\n\n"
        f"📊 *Статистика за сегодня:*\n"
        f"✅ *Съедено*: {consumed} ккал\n"
        f"🔻 *Осталось*: {remaining} ккал\n"
    )

    await message.answer(meal_text, parse_mode="Markdown")


@dp.message(F.photo)
async def process_photo(message: types.Message):
    """Обрабатывает фото и отправляет в OpenAI."""
    if not message.caption or not message.caption.strip().lower().startswith("/calc"):
        await message.answer("Чтобы рассчитать КБЖУ, отправьте фото с подписью, начинающейся с /calc.")
        return

    # Скачиваем фото
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    temp_filename = "temp_image.jpg"
    await bot.download_file(file.file_path, destination=temp_filename)

    # Кодируем фото в base64
    with open(temp_filename, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты — помощник по распознаванию блюд. "
                        "Если распознано блюдо, верни только JSON формата:\n"
                        "{\n"
                        "  \"название\": \"string\",\n"
                        "  \"вес_г\": 150,\n"
                        "  \"калории\": 52,\n"
                        "  \"белки_г\": 0.3,\n"
                        "  \"жиры_г\": 0.2,\n"
                        "  \"углеводы_г\": 14\n"
                        "}\n"
                        "Без дополнительных пояснений, без markdown. "
                        "Если на фото нет блюда, верни строго:\n"
                        "Блюдо не найдено"
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Определи, есть ли на фото блюдо. Если да — верни JSON, иначе — 'Блюдо не найдено'."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ],
                }
            ],
        )
        # Получаем ответ от OpenAI
        answer_content = response.choices[0].message.content.strip()

        # Проверяем, что OpenAI вернул корректный ответ
        if not answer_content:
            logging.error("⚠ OpenAI вернул пустой ответ.")
            await message.answer("❌ Ошибка обработки изображения. Попробуйте ещё раз позже.")
            return

        print(f"🔍 Ответ OpenAI: {answer_content}")  # Отладочный вывод

        # Если блюдо не найдено
        if "Блюдо не найдено" in answer_content:
            await message.answer("❌ Не удалось распознать блюдо.")
            return

        # Сохраняем результат в память
        meal_data = json.loads(answer_content)
        last_meals[message.from_user.id] = meal_data

        meal_text = (
            f"🍽 *Блюдо*: {meal_data.get('название')}\n"
            f"🔥 *Калории*: {meal_data.get('калории')} ккал\n"
            f"💪 *Белки*: {meal_data.get('белки_г')} г\n"
            f"🧈 *Жиры*: {meal_data.get('жиры_г')} г\n"
            f"🍞 *Углеводы*: {meal_data.get('углеводы_г')} г\n\n"
            f"✅ Если всё верно, отправьте /done, чтобы добавить в дневник."
        )

        # Отправляем пользователю
        await message.answer(meal_text, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Ошибка при запросе к OpenAI: {e}")
        await message.answer("Произошла ошибка при обработке изображения. Попробуйте ещё раз позже.")


async def main():
    """Запуск бота."""
    await create_db()
    await bot.set_my_commands(commands=[
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="calc", description="Рассчитать КБЖУ по фото"),
        BotCommand(command="done", description="Добавить последнее блюдо в дневник"),
        BotCommand(command="stats", description="Показать статистику за день"),
        BotCommand(command="reset", description="Сбросить статистику за день"),
        BotCommand(command="setgoal", description="Установить дневную норму калорий (/setgoal 2000)")
    ])

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
