import math
import logging
import json
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from google import genai
from google.genai import types

from config import GEMINI_API_KEYS
from database_manager import get_active_targets

logger = logging.getLogger(__name__)

router = Router()

# Для бота используем первый ключ (или отдельную логику)
genai_client = genai.Client(api_key=GEMINI_API_KEYS[0]) if GEMINI_API_KEYS else None

def haversine(lat1, lon1, lat2, lon2):
    """Вычисляет расстояние в километрах по формуле гаверсинуса (кривизна Земли)."""
    R = 6371.0 # Радиус Земли в километрах
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def categorize_distance(distance_km: float) -> str:
    if distance_km < 10:
        return "Критически близко (менее 10 км)"
    elif distance_km <= 30:
        return "В твоем районе (10-30 км)"
    elif distance_km <= 100:
        return "В пределах области (30-100 км)"
    else:
        return f"Безопасно (более 100 км)"

async def ask_gemini(user_query: str, extra_context: str = "") -> str:
    if not genai_client:
        return "❌ Ошибка системы связи: отсутствует ИИ-модуль."
        
    targets = get_active_targets()
    
    # Жесткий системный промпт диспетчера
    system_instruction = (
        "Ты — ИИ-Диспетчер SkyWatcher. Отвечай как профессиональный, спокойный военный диспетчер. "
        "Твоя задача — информировать пользователей, опираясь ТОЛЬКО на список ACTIVE_TARGETS. "
        "Если целей нет, отвечай 'В небе чисто, угроз нет'. "
        "Пиши коротко, по факту, без лишней паники и воды. Используй только текущие факты. "
        "Геолокация: Если тебя спрашивают 'Мне прятаться?' или 'Где летит?' без отправки функции 'Поделиться локацией' — "
        "обязательно скажи 'Нажмите кнопку 📍 «Проверить угрозу рядом со мной»'."
    )
    
    prompt = f"""
    === СИТУАЦИЯ НА РАДАРЕ ===
    ACTIVE_TARGETS:
    {json.dumps(targets, ensure_ascii=False) if targets else "ПУСТО (Небо чистое)"}
    
    {extra_context}
    
    === СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ ===
    {user_query}
    """
    
    try:
        response = await genai_client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2 # Чуть выше нуля, чтобы ответ звучал как текст, но без галлюцинаций
            ),
        )
        return response.text
    except Exception as e:
        logger.error(f"Generate Content Error (Bot Logic): {e}")
        return "⚠️ Временная потеря связи с аналитическим ядром."

@router.message(F.location)
async def handle_user_location(message: Message):
    """Обработчик отправки геопозиции пользователем."""
    user_lat = message.location.latitude
    user_lon = message.location.longitude
    
    targets = get_active_targets()
    
    if not targets:
        await message.answer("✅ В небе чисто. Никаких подтвержденных угроз на радаре нет.")
        return
        
    distances_info = []
    
    # Вычисляем дистанцию до всех целей
    for t_id, tgt in targets.items():
        if "lat" in tgt and "lon" in tgt:
            dist = haversine(user_lat, user_lon, tgt["lat"], tgt["lon"])
            cat = categorize_distance(dist)
            distances_info.append(f"Цель '{tgt.get('type', 'Unknown')}' находится на расстоянии: {dist:.1f} км. Категория: {cat}.")

    distances_str = "\n".join(distances_info)
    
    # Отправляем эти вычисления ИИ, чтобы он сгенерировал человечный текст
    extra_context = (
        "=== ИНФОРМАЦИЯ О ЛОКАЦИИ ===\n"
        "Пользователь предоставил свои GPS-координаты.\n"
        f"Система произвела математический расчет:\n{distances_str}\n"
        "Сформируй на основе этого итоговый вердикт (спокойно и четко)."
    )
    
    # Даем ИИ понять, что пользователь просто прислал локацию
    loading_msg = await message.answer("📡 Анализ расстояний (Haversine formula)...")
    
    ai_response = await ask_gemini("Где ближайшая цель ко мне?", extra_context)
    
    await loading_msg.edit_text(ai_response)

@router.message(F.text & ~F.text.startswith('/'))
async def handle_user_text(message: Message):
    """Обработка обычных текстовых запросов к Диспетчеру."""
    ai_response = await ask_gemini(message.text)
    await message.answer(ai_response)

# === ОТЛАДОЧНЫЕ КОМАНДЫ ДЛЯ ТЕСТИРОВАНИЯ КАРТЫ ===

@router.message(Command("test_target"))
async def cmd_test_target(message: Message):
    """Создает тестовую цель на карте."""
    import uuid
    import random
    from datetime import datetime, timezone
    from database_manager import update_active_target
    
    target_type = random.choice(["SHAHED", "ROCKET", "AVIATION"])
    speed = 180 if target_type == "SHAHED" else (900 if target_type == "AVIATION" else 2500)
    
    target_id = f"test-{uuid.uuid4().hex[:4]}"
    test_data = {
        "id": target_id,
        "type": target_type,
        "speed": speed,
        "lat": 48.37 + (random.uniform(-0.5, 0.5)), 
        "lon": 31.16 + (random.uniform(-0.5, 0.5)),
        "direction": random.choice(["N", "S", "W", "E", "NW", "NE", "SW", "SE"]),
        "threat_level": random.choice(["medium", "high", "critical"]),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    update_active_target(target_id, test_data)
    await message.answer(f"🚀 ТЕСТ: {target_type} запущен.\nСкорость: {speed} км/ч\nКурс: {test_data['direction']}")

@router.message(Command("test_alarm"))
async def cmd_test_alarm(message: Message):
    """Включает тревогу в регионе (напр. /test_alarm Київська область)."""
    region = message.text.replace("/test_alarm", "").strip()
    if not region:
        await message.answer("Укажите область, например: `/test_alarm Київська область`")
        return
    
    from database_manager import set_region_status
    set_region_status(region, True)
    await message.answer(f"🚨 Тревога в регионе [{region}] включена!")

@router.message(Command("test_clear"))
async def cmd_test_clear(message: Message):
    """Очищает все активные цели."""
    from database_manager import get_active_targets, delete_active_target
    targets = get_active_targets()
    count = 0
    for tid in list(targets.keys()):
        delete_active_target(tid)
        count += 1
    await message.answer(f"🧹 Карта очищена от целей ({count} шт.). Луганск и Крым останутся красными.")
