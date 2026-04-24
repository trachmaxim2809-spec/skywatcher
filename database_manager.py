import firebase_admin
from firebase_admin import credentials, db
import logging
import os

logger = logging.getLogger(__name__)

def init_firebase():
    """Инициализация подключения к Firebase Realtime Database."""
    # 1. Пытаемся взять данные из переменной окружения (для Render/Heroku)
    fb_json_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    
    try:
        if fb_json_env:
            import json
            # Создаем сертификат из строки JSON
            cred_dict = json.loads(fb_json_env)
            cred = credentials.Certificate(cred_dict)
            logger.info("Firebase Admin SDK инициализирован из переменной окружения.")
        else:
            # 2. Если переменной нет, ищем локальный файл
            creds_path = "skywatcher-3cf3f-firebase-adminsdk-fbsvc-df0a051709.json"
            if not os.path.exists(creds_path):
                logger.error("Ключи Firebase не найдены ни в ENV, ни в файле!")
                return False
            cred = credentials.Certificate(creds_path)
            logger.info(f"Firebase Admin SDK инициализирован из файла {creds_path}")

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://skywatcher-3cf3f-default-rtdb.europe-west1.firebasedatabase.app'
            })
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации Firebase: {e}")
        return False

def set_region_status(region_name: str, is_active: bool):
    """Меняет статус воздушной тревоги в регионе."""
    try:
        # Ссылка на узел regions/имя_региона
        ref = db.reference(f'regions/{region_name}')
        # Записываем true или false
        ref.set(is_active)
        logger.info(f"Статус региона '{region_name}' изменен на {is_active}")
        return True
    except Exception as e:
        logger.error(f"Ошибка записи в Firebase (регион {region_name}): {e}")
        return False
