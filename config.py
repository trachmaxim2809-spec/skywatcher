import os
from dotenv import load_dotenv

load_dotenv()

# Если токен не установлен в переменных окружения, используем заглушку для наглядности (лучше так не делать в проде)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEB_APP_URL = "https://trachmaxim2809-spec.github.io/skywatcher/"
