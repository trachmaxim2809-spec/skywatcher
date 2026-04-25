import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timedelta
import dateutil.parser

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

from config import GEMINI_API_KEYS
from database_manager import init_firebase, get_recent_raw_observations, get_active_targets, update_active_target, delete_active_target

logging.basicConfig(level=logging.INFO, format='%(asctime)s - HighCouncil - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ActiveTarget(BaseModel):
    id: str = Field(description="Уникальный ID цели (сохраняй старый для существующих, генерируй новый вида 'tgt-XXXX' для новых)")
    type: str = Field(description="Тип: SHAHED, ROCKET, AVIATION")
    lat: float = Field(description="Широта (центроид)")
    lon: float = Field(description="Долгота (центроид)")
    direction: Optional[str] = Field(description="Вектор движения: N, S, W, E, NW, NE, SW, SE", default=None)
    threat_level: str = Field(description="Уровень угрозы: low, medium, high, critical")

class HighCouncilResponse(BaseModel):
    targets: List[ActiveTarget]

# Пул клиентов Gemini для Верховного
clients = [genai.Client(api_key=key) for key in GEMINI_API_KEYS] if GEMINI_API_KEYS else []
current_key_idx = 0
council_semaphore = asyncio.Semaphore(len(GEMINI_API_KEYS) if GEMINI_API_KEYS else 1)

def get_next_client():
    global current_key_idx
    if not clients:
        raise ValueError("Нет ключей Gemini")
    client = clients[current_key_idx]
    current_key_idx = (current_key_idx + 1) % len(clients)
    return client

async def process_observations():
    """Сводит сырые данные в единые цели."""
    raw_obs = get_recent_raw_observations(5)
    if not raw_obs:
        logger.debug("Нет новых донесений за 5 минут. Отдыхаем.")
        return

    current_targets = get_active_targets()
    
    # Готовим промпт
    system_instruction = (
        "Ты — High Council AI (Командующий ПВО). Твоя задача: агрегация тактических ОТЧЕТОВ от 18 парсеров.\n"
        "ВАЖНО: Ты не видишь исходные сообщения, только структурированные данные (тип, координаты, уверенность, канал).\n"
        "ПРАВИЛО 1 (Слияние): Если несколько ОТЧЕТОВ описывают один объект (радиус 30-50 км), объедини их. "
        "ПРАВИЛО 2 (Мгновенная тактика): Каждое донесение от разведчика (NEW_OBSERVATIONS) должно быть немедленно учтено. "
        "Создавай новую цель или обновляй существующую в CURRENT_TARGETS на основе полученных координат без ожидания вторых источников.\n"
        "ПРАВИЛО 3 (ID Persistence): Сохраняй старые ID из CURRENT_TARGETS при обновлении позиций.\n"
        "ВЕРНИ ТОЛЬКО JSON список активных целей."
    )
    
    user_prompt = f"""
    CURRENT_TARGETS:
    {json.dumps(current_targets, ensure_ascii=False)}
    
    NEW_OBSERVATIONS (от парсеров за последние 5 мин):
    {json.dumps(raw_obs, ensure_ascii=False)}
    """
    
    async with council_semaphore:
        try:
            client = get_next_client()
            logger.info("Верховный ИИ анализирует тактическую обстановку...")
            
            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=HighCouncilResponse,
                    temperature=0.1
                ),
            )
            
            if not response.text:
                return
                
            data = json.loads(response.text)
            new_targets = data.get("targets", [])
            
            now_iso = datetime.now(timezone.utc).isoformat()
            
            # Сохраняем в базу новые и обновленные
            for tgt in new_targets:
                tgt_id = tgt["id"]
                tgt["last_updated"] = now_iso
                update_active_target(tgt_id, tgt)
                logger.info(f"📍 Цель подтверждена сервером: {tgt['type']} [{tgt_id}] @ {tgt['lat']}, {tgt['lon']}")
                
        except Exception as e:
            logger.error(f"Ошибка Верховного ИИ: {e}")

async def cleanup_old_targets():
    """Удаляет цели, которые не подтверждались более 10 минут."""
    targets = get_active_targets()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    for key, val in targets.items():
        updated_str = val.get("last_updated")
        if updated_str:
            last_up = dateutil.parser.isoparse(updated_str).replace(tzinfo=None)
            if last_up < cutoff:
                delete_active_target(key)
                logger.warning(f"🗑️ Цель {key} пропала с радаров (T+10). Удалил с карты.")

async def council_loop():
    logger.info("Верховный Совет (Диспетчер) заступил на боевое дежурство.")
    while True:
        await process_observations()
        await cleanup_old_targets()
        await asyncio.sleep(30) # Проверяем каждые 30 секунд

if __name__ == "__main__":
    init_firebase()
    asyncio.run(council_loop())
