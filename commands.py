import json
import logging
import base64

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ai import ai_process_image_and_addition
from db import (add_meal, get_meals_for_today, get_daily_calories,
                get_calories_consumed, reset_daily_meals, set_daily_goal,
                get_macros_for_today)

# Временное хранилище данных о последнем распознанном блюде (user_id -> meal_data)
_pending_meals: dict = {}

logging.basicConfig(level=logging.INFO)


async def start_command(message: types.Message):
    await message.answer("Привет! Отправь фото блюда, и я рассчитаю КБЖУ.")


async def done_command(message: types.Message):
    """Оставлена для обратной совместимости."""
    await message.answer("ℹ Теперь блюда добавляются автоматически после анализа фото.")


async def setgoal_command(message: types.Message):
    args = message.text.split()[1:]
    if not args or not args[0].isdigit():
        await message.answer("⚠ Укажите число, например: /setgoal 1800")
        return
    await set_daily_goal(message.from_user.id, int(args[0]))
    await message.answer(f"🎯 Ваша новая цель: {args[0]} ккал в день!")


async def stats_command(message: types.Message):
    await _send_stats(message.from_user.id, message.answer)


async def reset_command(message: types.Message):
    await reset_daily_meals(message.from_user.id)
    await message.answer("📭 Ваша статистика за сегодня обнулена!")


async def _send_stats(user_id: int, reply_func):
    """Формирует и отправляет полную статистику за день."""
    consumed = await get_calories_consumed(user_id)
    daily = await get_daily_calories(user_id)
    proteins, fats, carbs = await get_macros_for_today(user_id)
    meals = await get_meals_for_today(user_id)

    if meals:
        meals_text = "\n".join([
            f"🍽 {row[0]} — {row[1]} ккал"
            for row in meals
        ])
    else:
        meals_text = "📭 Нет записей"

    text = (
        f"📊 *Статистика на сегодня:*\n\n"
        f"🔥 *Калории*: {consumed} / {daily} ккал\n"
        f"💪 *Белки*: {proteins} г\n"
        f"🧈 *Жиры*: {fats} г\n"
        f"🍞 *Углеводы*: {carbs} г\n\n"
        f"🍽 *Съеденные блюда:*\n{meals_text}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить статистику", callback_data="reset_stats")],
    ])
    await reply_func(text, parse_mode="Markdown", reply_markup=keyboard)


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

    await add_meal(user_id, meal_name, calories)

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


async def process_photo_and_additional(message: types.Message):
    """Обрабатывает фото, анализирует через Mistral и предлагает добавить в дневник."""
    from bot import bot

    # Скачиваем фото
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    temp_filename = "temp_image.jpg"
    await bot.download_file(file.file_path, destination=temp_filename)

    # Кодируем фото в base64
    with open(temp_filename, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    additional_data = message.caption.strip() if message.caption else ""
    ai_response = None
    try:
        ai_response = await ai_process_image_and_addition(base64_image, additional_data)
    except Exception as e:
        logging.error(f"Ошибка при запросе к Mistral: {e}")
        await message.answer("Произошла ошибка при обработке изображения. Попробуйте ещё раз позже.")
        return

    if not ai_response:
        logging.error("⚠ Mistral вернул пустой ответ.")
        await message.answer("❌ Ошибка обработки изображения. Попробуйте ещё раз позже.")
        return

    if "Блюдо не найдено" in ai_response:
        await message.answer("❌ Не удалось распознать блюдо.")
        return

    meal_data = json.loads(ai_response)
    user_id = message.from_user.id

    # Сохраняем данные о блюде — ждём решения пользователя
    _pending_meals[user_id] = meal_data

    meal_text = (
        f"🍽 *Блюдо*: {meal_data.get('название')}\n"
        f"🍏 *Вес*: {meal_data.get('вес_г')} г\n"
        f"🔥 *Калории*: {meal_data.get('калории')} ккал\n"
        f"💪 *Белки*: {meal_data.get('белки_г')} г\n"
        f"🧈 *Жиры*: {meal_data.get('жиры_г')} г\n"
        f"🍞 *Углеводы*: {meal_data.get('углеводы_г')} г\n"
        f"💩 *Калорийность на 100г*: {meal_data.get('калорийность_на_100г')} ккал"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Добавить в дневник", callback_data="add_meal")],
        [InlineKeyboardButton(text="📊 Посмотреть всё", callback_data="show_stats")],
    ])

    await message.answer(meal_text, parse_mode="Markdown", reply_markup=keyboard)


async def add_meal_callback(callback: types.CallbackQuery):
    """Добавляет последнее распознанное блюдо в дневник и показывает статистику."""
    user_id = callback.from_user.id
    meal_data = _pending_meals.pop(user_id, None)

    if not meal_data:
        await callback.answer("Нет данных о блюде. Отправьте фото заново.", show_alert=True)
        return

    await add_meal(
        user_id,
        meal_data.get("название", ""),
        meal_data.get("калории", 0),
        proteins=meal_data.get("белки_г", 0),
        fats=meal_data.get("жиры_г", 0),
        carbs=meal_data.get("углеводы_г", 0),
    )

    await callback.message.edit_reply_markup(reply_markup=None)

    consumed = await get_calories_consumed(user_id)
    daily = await get_daily_calories(user_id)
    proteins, fats, carbs = await get_macros_for_today(user_id)
    remaining = daily - consumed

    confirm_text = (
        f"✅ *Блюдо добавлено в дневник!*\n\n"
        f"📊 *Статистика на сегодня:*\n"
        f"🔥 *Калории*: {consumed} / {daily} ккал\n"
        f"🔻 *Осталось*: {remaining} ккал\n"
        f"💪 *Белки*: {proteins} г\n"
        f"🧈 *Жиры*: {fats} г\n"
        f"🍞 *Углеводы*: {carbs} г"
    )

    await callback.message.answer(confirm_text, parse_mode="Markdown")
    await callback.answer()


async def show_stats_callback(callback: types.CallbackQuery):
    """Показывает текущую статистику за день без добавления блюда."""
    await _send_stats(callback.from_user.id, callback.message.answer)
    await callback.answer()


async def reset_stats_callback(callback: types.CallbackQuery):
    """Сбрасывает статистику за день."""
    await reset_daily_meals(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("🗑 Статистика за сегодня очищена!")
    await callback.answer()
