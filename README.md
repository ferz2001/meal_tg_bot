
# 🍽 Telegram-бот для учета калорий

Этот бот помогает отслеживать дневное потребление калорий, распознавая блюда по фото и вычисляя их КБЖУ (калории, белки, жиры, углеводы). Бот записывает съеденные продукты и выводит статистику за день.

---

## **🚀 Установка и запуск**

1. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/ferz2001/meal_tg_bot
   cd MealTgBot
   ```

2. **Создайте виртуальное окружение**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Для Linux/Mac
   .venv\Scripts\activate     # Для Windows
   ```

3. **Установите зависимости**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте переменные в `.env`**:
   Создайте файл `.env` с вашими API-ключами:
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен_бота
   OPENAI_API_KEY=ваш_openai_ключ
   ```

5. **Запустите бота**:
   ```bash
   python main.py
   ```

---

## **📌 Команды**

- **/start** — Запустить бота.
- **/calc** — Отправьте фото с подписью `/calc`, чтобы распознать блюдо и получить его КБЖУ.
- **/done** — Добавить последнее распознанное блюдо в дневник.
- **/stats** — Показать статистику за день.
- **/reset** — Сбросить статистику за день.
- **/setgoal [калории]** — Установить дневную норму калорий.

---

## **📌 Структура проекта**

```
.
├── db.py                # Модуль работы с SQLite
├── main.py              # Основной код бота
├── .env                 # Файл конфигурации с ключами API
└── requirements.txt     # Зависимости проекта
```

---

## **📌 Лицензия**

Этот проект распространяется под лицензией MIT.
