import logging
import asyncio
from functools import partial

from mistralai.client import MistralClient

from config import settings


client = MistralClient(api_key=settings.MISTRAL_API_KEY)
logging.basicConfig(level=logging.INFO)


async def ai_process_image_and_addition(image_data, additional_data):
    """
    Отправляет изображение и дополнение в Mistral AI для обработки.

    Args:
        image_data (str): Изображение, закодированное в base64, которое будет отправлено в Mistral для распознавания.
        additional_data (str): Дополнительные данные от пользователя, которые могут помочь в распознавании блюда.

    Returns:
        str: Ответ от Mistral, содержащий JSON с данными о блюде (название, вес, калории и т.д.)
        или строку 'Блюдо не найдено'.

    """
    messages = [
        {
            "role": "system",
            "content": (
                "Ты — помощник по распознаванию блюд и расчёту КБЖУ блюда по фото или описанию. "
                "Если на фото нет блюда, но в дополнении указаны детали (например, 'кофе с молоком 300мл'), "
                "используй информацию из дополнения для формирования ответа. "
                "Если трудно вычислить калорийность, лучше сделай её более высокой, чем ниже. "
                "Наша цель похудеть."
                "Если распознано блюдо, верни только JSON формата без дополнений и без markdown:\n"
                "{\n"
                "  \"название\": \"string\",\n"
                "  \"вес_г\": 16,\n"
                "  \"калории\": 52,\n"
                "  \"белки_г\": 0.3,\n"
                "  \"жиры_г\": 0.2,\n"
                "  \"углеводы_г\": 14\n"
                "  \"калорийность_на_100г\": 321,\n"
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

    loop = asyncio.get_event_loop()
    func = partial(
        client.chat,
        model="pixtral-12b-2409",
        messages=messages,
    )
    response = await loop.run_in_executor(None, func)

    print(response)
    print(response.choices[0].message.content.strip())
    return response.choices[0].message.content.strip()
