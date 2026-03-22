import logging
import asyncio
import httpx

from config import settings

logging.basicConfig(level=logging.INFO)

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


async def ai_process_image_and_addition(image_data, additional_data):
    """
    Отправляет изображение и дополнение в Mistral AI для обработки.

    Args:
        image_data (str): Изображение, закодированное в base64.
        additional_data (str): Дополнительные данные от пользователя.

    Returns:
        str: JSON с данными о блюде или строку 'Блюдо не найдено'.
    """
    payload = {
        "model": "pixtral-12b-2409",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты — помощник по распознаванию блюд и расчёту КБЖУ блюда по фото или описанию. "
                    "Если на фото нет блюда, но в дополнении указаны детали (например, 'кофе с молоком 300мл'), "
                    "используй информацию из дополнения для формирования ответа. "
                    "Если трудно вычислить калорийность, лучше сделай её более высокой, чем ниже. "
                    "Наша цель похудеть. "
                    "Если распознано блюдо, верни только JSON формата без дополнений и без markdown:\n"
                    "{\n"
                    "  \"название\": \"string\",\n"
                    "  \"вес_г\": 16,\n"
                    "  \"калории\": 52,\n"
                    "  \"белки_г\": 0.3,\n"
                    "  \"жиры_г\": 0.2,\n"
                    "  \"углеводы_г\": 14,\n"
                    "  \"калорийность_на_100г\": 321\n"
                    "}\n"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Определи, есть ли на фото блюдо или в дополнении. "
                            "Если да — верни JSON, иначе — 'Блюдо не найдено'. "
                            "Если в дополнении несколько блюд, добавляй КБЖУ остальных блюд "
                            "и формируй из них общее название. "
                            "Если на фото нет блюда или информация о весе/составе неполная, используй данные, "
                            "предоставленные пользователем в виде дополнения и хоть как сформируй ответ. "
                            f"Дополнение: {additional_data}. "
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{image_data}"
                    }
                ]
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(MISTRAL_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"].strip()
    logging.info(f"Mistral response: {content}")

    # Strip markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]).strip()

    # Handle array response — take first element
    import json
    parsed = json.loads(content)
    if isinstance(parsed, list):
        parsed = parsed[0]

    return json.dumps(parsed, ensure_ascii=False)
