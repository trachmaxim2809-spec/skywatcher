import firebase_admin
from firebase_admin import credentials, db
import logging
import os

logger = logging.getLogger(__name__)

def init_firebase():
    """Инициализация подключения к Firebase Realtime Database."""
    creds_path = "skywatcher-3cf3f-firebase-adminsdk-fbsvc-df0a051709.json"
    
    # Проверяем наличие ключа Service Account
    if not os.path.exists(creds_path):
        logger.error(f"Файл ключа {creds_path} не найден! Firebase не работает.")
        return False
        
    try:
        # Инициализируем Admin SDK с URL нашей базы данных
        cred = credentials.Certificate(creds_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://skywatcher-3cf3f-default-rtdb.europe-west1.firebasedatabase.app'
        })
        logger.info("Firebase Admin SDK успешно инициализирован.")
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
