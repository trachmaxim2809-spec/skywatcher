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

class EstimatedCoords(BaseModel):
    lat: float
    lon: float

class GeminiObservation(BaseModel):
    detected_object: Optional[str] = Field(description="Только: 'SHAHED', 'ROCKET', 'AVIATION' или null")
    confidence: Optional[float] = Field(description="Уверенность 0.0-1.0. Если меньше 0.8 — верни null для detected_object")
    region_tag: Optional[str] = Field(description="Название области или региона")
    estimated_coords: Optional[EstimatedCoords] = Field(description="Координаты, если применимо", default=None)
    direction_vector: Optional[str] = Field(description="Только: 'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW' или null")
    raw_urgency: Optional[str] = Field(description="Только: 'low', 'medium', 'high', 'critical'")
    alarm_status: Optional[bool] = Field(description="True если в тексте сообщение о НАЧАЛЕ или ПРЯМОМ НАЛИЧИИ тревоги, False если ОБ ОТБОЕ, null если не упоминается")

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

async def analyze_message(text: str, channel_raw_name: str, region_context: str = None) -> Optional[dict]:
    """Анализирует текст и возвращает словарь с данными или None при ошибке/отсутствии угрозы."""
    if not pre_filter_text(text):
        return None
        
    regional_prompt = ""
    if region_context and region_context != "Вся Україна":
        regional_prompt = f"\nПРЕДУПРЕЖДЕНИЕ: Это сообщение из проверенного источника по региону [{region_context}]. Если в тексте нет явных уточнений города, считай, что события (пролеты, взрывы) происходят именно в этом регионе. Обязательно укажи этот регион в region_tag.\n"

    system_instruction = (
        "Ты — тактический терминал сбора данных SkyWatcher. Твоя единственная цель: извлечение координат и типов угроз из хаотичного текста.\n"
        "ПРАВИЛО №1 (FORMAT): Ответ ДОЛЖЕН содержать ТОЛЬКО чистый JSON. Любое пояснение, текст 'Вот ваш JSON' или вежливость — это системная ошибка. Если данных нет, верни {\"detected_object\": null}.\n"
        "ПРАВИЛО №2 (IDENTIFICATION): Угроза 'SHAHED': мопеды, балалайки, газонокосилки, скутеры, 'шах', 'герань', 'жужжание'. "
        "Угроза 'ROCKET': сушки, изделия, подарки, выходы, баллистика, Х-101, Х-59, Калибры, 'бавовна' (если в контексте прилета), Кинжал, Искандер. "
        "Угроза 'AVIATION': МиГ-31К, Ту-95, Ту-22, дозаправка в воздухе.\n"
        "ПРАВИЛО №3 (GEOGRAPHY & CONTEXT): "
        "Если указано направление (на запад), вычисли вектор движения. "
        "Если источник в локальном контексте и пишет 'слышны взрывы' или сообщает о ЛЮБОЙ активной угрозе (detected_object не null), "
        "ТЫ ОБЯЗАН в этом же ответе выставить alarm_status в True. Твоя задача — зажечь область на карте при малейшей опасности.\n"
        "Игнорируй сборы на дроны, политику и погоду. Только активные цели.\n"
        "ПРАВИЛО №4 (STRICT OUTPUT SCHEMA): "
        "Галлюцинации запрещены. Если уверенность ниже 80% — ставь detected_object в null."
        f"{regional_prompt}"
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
            
            # Принудительно устанавливаем регион, если он был передан (чтобы ИИ не ошибся)
            if region_context and region_context != "Вся Україна" and not data.get("region_tag"):
                 data["region_tag"] = region_context
                
            obj = data.get("detected_object")
            if not obj:
                logger.info(f"🤖 Вердикт ИИ: Объектов не обнаружено (Шум/Спам).")
                return None # Угрозы нет, игнорим
                
            logger.warning(f"🚀 Вердикт ИИ: ОБНАРУЖЕН {obj}! (Confidence: {data.get('confidence')})")
            return data
            
        except Exception as e:
            logger.error(f"Ошибка Gemini API: {e}")
            return None
