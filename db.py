import aiosqlite
from datetime import date

DB_NAME = "calories.db"


async def create_db():
    """Создаёт базу данных и необходимые таблицы, если их ещё нет."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            daily_calories INTEGER DEFAULT 2000
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            calories INTEGER,
            date TEXT
        )
        """)
        await db.commit()


async def add_meal(user_id: int, name: str, calories: int):
    """Добавляет запись о блюде в дневник."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT INTO meals (user_id, name, calories, date)
        VALUES (?, ?, ?, ?)
        """, (user_id, name, calories, date.today().isoformat()))
        await db.commit()


async def get_meals_for_today(user_id: int):
    """Возвращает список блюд (название и калории) за сегодняшний день."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT name, calories FROM meals
        WHERE user_id = ? AND date = ?
        """, (user_id, date.today().isoformat()))
        meals = await cursor.fetchall()
        return meals


async def get_daily_calories(user_id: int):
    """Возвращает дневную норму калорий для пользователя. Если записи нет – создаёт со значением 2000."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT daily_calories FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        if result:
            return result[0]
        else:
            await db.execute("INSERT INTO users (user_id, daily_calories) VALUES (?, ?)", (user_id, 2000))
            await db.commit()
            return 2000


async def get_calories_consumed(user_id: int):
    """Возвращает суммарное количество калорий, съеденных сегодня."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT SUM(calories) FROM meals
        WHERE user_id = ? AND date = ?
        """, (user_id, date.today().isoformat()))
        result = await cursor.fetchone()
        return result[0] if result[0] is not None else 0


async def reset_daily_meals(user_id: int):
    """Удаляет все записи о блюдах за сегодняшний день для данного пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        DELETE FROM meals
        WHERE user_id = ? AND date = ?
        """, (user_id, date.today().isoformat()))
        await db.commit()


async def set_daily_goal(user_id: int, calories: int):
    """Устанавливает новую дневную норму калорий для пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT INTO users (user_id, daily_calories)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET daily_calories = excluded.daily_calories
        """, (user_id, calories))
        await db.commit()
