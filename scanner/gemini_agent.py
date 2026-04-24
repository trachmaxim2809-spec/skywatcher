import asyncio
import logging
import re
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional

from config import GEMINI_API_KEYS

logger = logging.getLogger(__name__)

class GeminiObservation(BaseModel):
    detected_object: Optional[str] = Field(description="Тип объекта: 'SHAHED', 'ROCKET', или null/None если воздушной угрозы нет. Сленг 'мопеды', 'балалайки', 'газонокосилки', 'скутеры' -> SHAHED. Сленг 'сушки', 'изделия', 'подарки', 'выходы', 'баллистика', 'х-101' -> ROCKET.")
    inferred_coords: Optional[str] = Field(description="Географические ориентиры, населенные пункты или координаты, упомянутые в тексте")
    direction: Optional[str] = Field(description="Направление движения объекта, например 'на северо-запад' или 'в сторону Киева'")
    region_tag: Optional[str] = Field(description="Название области (на украинском, напр. 'Київська область'), если понятно из текста")

# Пул клиентов Gemini
clients = [genai.Client(api_key=key) for key in GEMINI_API_KEYS] if GEMINI_API_KEYS else []
current_key_idx = 0

# Семафор на X одновременных запросов (по одному на ключ)
gemini_semaphore = asyncio.Semaphore(len(GEMINI_API_KEYS) if GEMINI_API_KEYS else 1)

def get_next_client():
    global current_key_idx
    if not clients:
        raise ValueError("Нет доступных ключей Gemini")
    
    client = clients[current_key_idx]
    current_key_idx = (current_key_idx + 1) % len(clients)
    return client

def pre_filter_text(text: str) -> bool:
    """Фильтрует рекламные или пустые сообщения Regex-ом (возвращает True, если стоит анализировать)."""
    if not text or len(text) < 5:
        return False
    
    # Игнорируем явную рекламу или спам
    spam_keywords = r"(промокод|подписывайтесь|скидка|казино|реклама|ставка|t\.me/|кликни|link|[🎰🎲💸])"
    if re.search(spam_keywords, text, re.IGNORECASE):
        return False
        
    return True

async def analyze_message(text: str, channel_raw_name: str) -> Optional[dict]:
    """Анализирует текст и возвращает словарь с данными или None при ошибке/отсутствии угрозы."""
    if not pre_filter_text(text):
        return None
        
    system_instruction = (
        "Ты военный ИИ-аналитик. Твоя задача "
        "анализировать тексты из Telegram-каналов о воздушных угрозах в Украине. "
        "Категория SHAHED: мопеды, балалайки, газонокосилки, скутеры. "
        "Категория ROCKET: сушки, изделия, подарки, выходы, баллистика, х-101. "
        "Верни строго JSON по заданной схеме. Если угрозы нет, поле detected_object пусть будет null."
    )
    
    async with gemini_semaphore:
        try:
            client = get_next_client()
        except ValueError:
            logger.error("Нет ключей Gemini в пуле!")
            return None
            
        logger.debug(f"Используем Gemini API Key по индексу: {clients.index(client)}")
        
        try:
            # Асинхронный вызов google-genai
            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=GeminiObservation,
                    temperature=0.0 # Минимизируем галлюцинации
                ),
            )
            
            if not response.text:
                return None
                
            data = json.loads(response.text)
            
            # Принудительные теги для локальных каналов
            channel_lower = channel_raw_name.lower()
            if "kyiv_nebo" in channel_lower or "kievreal" in channel_lower:
                data["region_tag"] = "Київська область"
                
            if not data.get("detected_object"):
                return None # Угрозы нет, игнорим
                
            return data
            
        except Exception as e:
            logger.error(f"Ошибка Gemini API: {e}")
            return None
