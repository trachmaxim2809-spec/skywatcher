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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Часовые (Глобальные и приоритетные каналы, способные включать тревогу)
PRIMARY_CHANNELS = ['air_force_ua', 'povitryana_tryvoga_official', 'war_monitor'] 
# Формируем полный список наблюдаемых каналов (Разведчики + Часовые) из конфига
ALL_CHANNELS = list(CHANNEL_REGION_MAP.keys())

session_name = "skywatcher_scanner"
client = TelegramClient(session_name, TG_API_ID, TG_API_HASH)

@client.on(events.NewMessage(chats=ALL_CHANNELS))
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
    
    # 2. Логика "ВЫСШЕГО ДОПУСКА" (Часовые)
    # Если это официальный канал и мы смогли вычленить регион — сразу бьем тревогу на карте!
    is_primary = any(p_chan.lower() in channel_name.lower() for p_chan in PRIMARY_CHANNELS)
    
    if is_primary and region:
        logger.warning(f"🚨 ЧАСОВОЙ ({channel_name}) доложил об угрозе в {region}! Включаю тревогу на карте!")
        set_region_status(region, True)
    else:
        logger.info(f"🕵️ РАЗВЕДЧИК ({channel_name}) доложил об активности (Объект: {observation.get('detected_object')}). Передаю в raw_observations.")
    
    # 3. Сохраняем сырые сканированные данные для Высших Агентов (в Части 7)
    save_raw_observation(observation)


async def main():
    if not TG_API_ID or not TG_API_HASH:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: TG_API_ID или TG_API_HASH не установлены в .env!")
        return

    logger.info("Инициализация соединения с базой Firebase...")    
    init_firebase()
    
    logger.info("Запуск Telegram-сканера (Userbot)...")
    # При первом запуске в консоли потребуется ввести номер телефона и код из Telegram
    await client.start()
    
    logger.info(f"👁️ Сканер успешно запущен. Мониторинг {len(ALL_CHANNELS)} каналов активен...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
