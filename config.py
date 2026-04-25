import os
from dotenv import load_dotenv

load_dotenv()

# Если токен не установлен в переменных окружения, используем заглушку для наглядности (лучше так не делать в проде)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEB_APP_URL = "https://trachmaxim2809-spec.github.io/skywatcher/"

TG_API_ID = int(os.getenv("TG_API_ID", 0))
TG_API_HASH = os.getenv("TG_API_HASH", "")

# Получаем и парсим ключи Gemini
raw_api_keys = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS = [key.strip() for key in raw_api_keys.split(",")] if raw_api_keys else []

# Маппинг Telegram-каналов на конкретные регионы (Основа для масштабирования на 24+ областей)
CHANNEL_REGION_MAP = {
    'kyiv_nebo': 'Київська область',
    'kievreal1': 'Київська область',
    'vanek_nikolaev': 'Миколаївська область',
    'kherson_nebo': 'Херсонська область',
    'odesa_monitor': 'Одеська область',
    'lviv_nebo': 'Львівська область',
    'dnipro_operativ': 'Дніпропетровська область',
    'kharkiv_life': 'Харківська область',
    'zaporizhzhia_now': 'Запорізька область',
    # Глобальные каналы
    'air_force_ua': 'Вся Україна',
    'povitryana_tryvoga_official': 'Вся Україна',
    'war_monitor': 'Вся Україна'
}
