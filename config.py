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
