import json
import logging
import base64

from aiogram import types

from ai import ai_process_image_and_addition
from db import (add_meal, get_meals_for_today, get_daily_calories,
                get_calories_consumed, reset_daily_meals, set_daily_goal)

last_meals = {}
logging.basicConfig(level=logging.INFO)


async def start_command(message: types.Message):
    await message.answer("Привет! Отправь фото блюда с подписью, начинающейся с /calc.")


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


async def setgoal_command(message: types.Message):
    args = message.text.split()[1:]
    if not args or not args[0].isdigit():
        await message.answer("⚠ Укажите число, например: /setgoal 1800")
        return
    await set_daily_goal(message.from_user.id, int(args[0]))
    await message.answer(f"🎯 Ваша новая цель: {args[0]} ккал в день!")


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


async def reset_command(message: types.Message):
    await reset_daily_meals(message.from_user.id)
    await message.answer("📭 Ваша статистика за сегодня обнулена!")


async def process_photo_and_additional(message: types.Message):
    """Обрабатывает фото и отправляет в OpenAI."""
    if not message.caption or not message.caption.strip().lower().startswith("/calc"):
        await message.answer("Чтобы рассчитать КБЖУ, отправьте фото с подписью, начинающейся с /calc.")
        return

    from bot import bot

    # Скачиваем фото
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    temp_filename = "temp_image.jpg"
    await bot.download_file(file.file_path, destination=temp_filename)

    # Кодируем фото в base64
    with open(temp_filename, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    additional_data = ' '.join(message.caption.split()[1:])
    ai_response = None
    try:
        ai_response = await ai_process_image_and_addition(base64_image, additional_data)
    except Exception as e:
        logging.error(f"Ошибка при запросе к OpenAI: {e}")
        await message.answer("Произошла ошибка при обработке изображения. Попробуйте ещё раз позже.")


    # Проверяем, что OpenAI вернул корректный ответ
    if not ai_response:
        logging.error("⚠ OpenAI вернул пустой ответ.")
        await message.answer("❌ Ошибка обработки изображения. Попробуйте ещё раз позже.")
        return

    # Если блюдо не найдено
    if "Блюдо не найдено" in ai_response:
        await message.answer("❌ Не удалось распознать блюдо.")
        return

    meal_data = json.loads(ai_response)
    last_meals[message.from_user.id] = meal_data

    meal_text = (
        f"🍽 *Блюдо*: {meal_data.get('название')}\n"
        f"🍏 *Вес*: {meal_data.get('вес_г')}\n"
        f"🔥 *Калории*: {meal_data.get('калории')} ккал\n"
        f"💪 *Белки*: {meal_data.get('белки_г')} г\n"
        f"🧈 *Жиры*: {meal_data.get('жиры_г')} г\n"
        f"🍞 *Углеводы*: {meal_data.get('углеводы_г')} г\n"
        f"💩 *Калорийность на 100гр*: {meal_data.get('калорийность_на_100г')} ккал\n"
        f"✅ Если всё верно, отправьте /done, чтобы добавить в дневник."
    )

    # Отправляем пользователю
    await message.answer(meal_text, parse_mode="Markdown")


async def eat_command(message: types.Message):
    """Добавляет блюдо в дневник вручную."""
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        await message.answer("⚠ Некорректный формат. Используйте:\n/eat 'Название блюда' 'Калорийность'")
        return

    meal_name = args[1].strip()
    try:
        calories = int(args[2].strip())
    except ValueError:
        await message.answer("⚠ Калорийность должна быть целым числом!")
        return

    # Добавляем в базу данных
    await add_meal(user_id, meal_name, calories)

    # Получаем обновленную статистику
    consumed = await get_calories_consumed(user_id)
    remaining = (await get_daily_calories(user_id)) - consumed

    meal_text = (
        f"✅ *Блюдо добавлено!*\n\n"
        f"🍽 *Название*: {meal_name}\n"
        f"🔥 *Калории*: {calories} ккал\n\n"
        f"📊 *Обновленная статистика:*\n"
        f"✅ *Съедено*: {consumed} ккал\n"
        f"🔻 *Осталось*: {remaining} ккал\n"
    )

    await message.answer(meal_text, parse_mode="Markdown")
