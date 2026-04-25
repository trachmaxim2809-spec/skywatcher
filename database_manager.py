import firebase_admin
from firebase_admin import credentials, db
import logging
import os

logger = logging.getLogger(__name__)

HARDCODED_ALARM_REGIONS = ["Луганська область", "Автономна Республіка Крим"]

def enforce_hardcoded_regions():
    """Жестко устанавливает красную тревогу для оккупированных территорий."""
    try:
        if not firebase_admin._apps:
            return
        ref = db.reference('regions')
        for region in HARDCODED_ALARM_REGIONS:
            ref.child(region).set(True)
    except Exception as e:
        logger.error(f"Ошибка установки жестких тревог: {e}")

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
            
        enforce_hardcoded_regions()
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации Firebase: {e}")
        return False

def set_region_status(region_name: str, is_active: bool):
    """Меняет статус воздушной тревоги в регионе."""
    try:
        # Проверяем, инициализирован ли Firebase
        if not firebase_admin._apps:
            return False, "Firebase не инициализирован. Ключи отсутствуют или неверны."
            
        # Защита Hardcoded-регионов от отключения тревоги
        if not is_active and region_name in HARDCODED_ALARM_REGIONS:
            logger.info(f"🛡️ Отклонено снятие тревоги для {region_name} (Закон Архитектуры).")
            return True, "Успешно (Тревога оставлена принудительно)"
            
        # Ссылка на узел regions/имя_региона
        ref = db.reference(f'regions/{region_name}')
        # Записываем true или false
        ref.set(is_active)
        logger.info(f"Статус региона '{region_name}' изменен на {is_active}")
        return True, "Успешно"
    except Exception as e:
        logger.error(f"Ошибка записи в Firebase (регион {region_name}): {e}")
        return False, str(e)

def save_raw_observation(data: dict):
    """Сохраняет сырые результаты парсинга (от Разведчиков) в Firebase."""
    try:
        if not firebase_admin._apps:
            return False, "Firebase не инициализирован."
        
        from datetime import datetime
        import uuid
        
        obs_id = str(uuid.uuid4())
        data["timestamp"] = datetime.utcnow().isoformat()
        
        ref = db.reference(f'raw_observations/{obs_id}')
        ref.set(data)
        logger.info(f"Новое наблюдение сохранено: {obs_id} (Объект: {data.get('detected_object')})")
        return True, "Успешно"
    except Exception as e:
        logger.error(f"Ошибка записи наблюдения в Firebase: {e}")
        return False, str(e)

def get_recent_raw_observations(minutes_ago: int = 5):
    """Возвращает наблюдения за последние N минут."""
    try:
        from datetime import datetime, timedelta
        import dateutil.parser
        
        ref = db.reference('raw_observations')
        data = ref.get() or {}
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_ago)
        recent = {}
        for k, v in data.items():
            ts_str = v.get("timestamp")
            if ts_str:
                obs_time = dateutil.parser.isoparse(ts_str)
                # Убираем timezone если она есть для честного сравнения (или делаем обе naive)
                obs_time = obs_time.replace(tzinfo=None)
                if obs_time >= cutoff_time:
                    recent[k] = v
        return recent
    except Exception as e:
        logger.error(f"Ошибка чтения raw_observations: {e}")
        return {}

def get_active_targets():
    """Возвращает текущие активные цели."""
    try:
        ref = db.reference('active_targets')
        return ref.get() or {}
    except Exception as e:
        logger.error(f"Ошибка чтения active_targets: {e}")
        return {}

def update_active_target(target_id: str, data: dict):
    """Обновляет или добавляет активную цель."""
    try:
        ref = db.reference(f'active_targets/{target_id}')
        ref.set(data)
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления active_targets: {e}")
        return False

def delete_active_target(target_id: str):
    """Удаляет активную цель (очистка)."""
    try:
        ref = db.reference(f'active_targets/{target_id}')
        ref.delete()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления active_targets: {e}")
        return False
