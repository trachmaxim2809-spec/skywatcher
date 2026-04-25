import asyncio
import logging
import sys
import os

# Добавляем родительскую директорию в PYTHONPATH чтобы найти модули верхнего уровня
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient, events
from config import TG_API_ID, TG_API_HASH, CHANNEL_REGION_MAP
from database_manager import init_firebase, set_region_status, save_raw_observation
from scanner.gemini_agent import analyze_message

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Часовые (Глобальные и приоритетные каналы, способные включать тревогу)
PRIMARY_CHANNELS = ['air_force_ua', 'povitryana_tryvoga_official', 'war_monitor'] 
# Формируем полный список наблюдаемых каналов (Разведчики + Часовые) из конфига
ALL_CHANNELS = list(CHANNEL_REGION_MAP.keys())

session_name = "skywatcher_scanner"
client = TelegramClient(session_name, TG_API_ID, TG_API_HASH)

async def handle_new_message(event):
    chat = await event.get_chat()
    channel_name = getattr(chat, 'username', None) or getattr(chat, 'title', 'unknown_channel')
    
    text = getattr(event.message, 'message', '')
    if not text:
        return
        
    logger.info(f"[{channel_name}] Новое сообщение, передаю агенту на анализ...")
    
    # 1. Запускаем анализ Gemini Agent (Pre-filter включен внутри него), передаем регион-контекст из конфига
    region_context = CHANNEL_REGION_MAP.get(channel_name.lower())
    observation = await analyze_message(text, channel_name, region_context=region_context)
    
    if not observation:
        logger.debug(f"[{channel_name}] Проигнорировано (нет угроз или спам)")
        return
        
    # Добавляем технические метаданные
    observation["source_channel"] = channel_name
    
    region = observation.get("region_tag")
    
    # 2. Логика АВТОМАТИЧЕСКОЙ ТРЕВОГИ
    # Если разведчик доложил о начале тревоги (alarm_status = True)
    alarm_reported = observation.get("alarm_status")
    
    if region:
        if alarm_reported is True:
            logger.warning(f"🚨 ОБНАРУЖЕНА ТРЕВОГА: {channel_name} доложил о начале тревоги в {region}!")
            set_region_status(region, True)
        elif alarm_reported is False:
            logger.info(f"🟢 ОТБОЙ: {channel_name} доложил об окончании тревоги в {region}.")
            set_region_status(region, False)
            
    # Дополнительно: Если это официальный канал ("Часовой")
    is_primary = any(p_chan.lower() in channel_name.lower() for p_chan in PRIMARY_CHANNELS)
    if is_primary and region and observation.get("detected_object"):
        logger.warning(f"🚨 ЧАСОВОЙ ({channel_name}) зафиксировал угрозу в {region}! Включаю тревогу!")
        set_region_status(region, True)

    # 3. Сохраняем сырые сканированные данные для Высшего Совета
    save_raw_observation(observation)

# === ОТЛАДОЧНЫЙ ЛОУДЕР (Ловим всё для проверки связи) ===
@client.on(events.NewMessage)
async def debug_all_messages(event):
    chat = await event.get_chat()
    chat_title = getattr(chat, 'title', 'Unknown')
    username = getattr(chat, 'username', 'NoUsername')
    logger.debug(f"[DEBUG RAW] Сообщение из: {chat_title} (@{username})")


async def main():
    if not TG_API_ID or not TG_API_HASH:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: TG_API_ID или TG_API_HASH не установлены в .env!")
        return

    logger.info("Инициализация соединения с базой Firebase...")    
    init_firebase()
    
    logger.info("Запуск Telegram-сканера (Userbot)...")
    await client.start()
    
    valid_channels = []
    logger.info("Проверка доступности каналов из конфигурации...")
    for ch in ALL_CHANNELS:
        try:
            # Пытаемся получить сущность канала
            await client.get_entity(ch)
            valid_channels.append(ch)
            logger.debug(f"[OK] Канал {ch} доступен.")
        except Exception as e:
            logger.warning(f"[SKIP] Канал '{ch}' недоступен или не существует: {e}")
            
    if not valid_channels:
        logger.error("Нет доступных каналов для мониторинга! Проверьте config.py")
        return
        
    client.add_event_handler(handle_new_message, events.NewMessage(chats=valid_channels))
    
    logger.info(f"👁️ Сканер безупречно запущен. Мониторинг {len(valid_channels)} проверенных каналов активен...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
